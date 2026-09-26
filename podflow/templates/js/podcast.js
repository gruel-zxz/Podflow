(() => {
    "use strict";

    /* ---------- 通用工具 ---------- */

    // 封面/单集图加载失败时统一使用的兜底图
    const FALLBACK_COVER = "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png";
    const withCoverFallback = (imgEl) => {
        imgEl.addEventListener("error", () => {
            if (imgEl.src === FALLBACK_COVER) return;   // 兜底图本身也加载失败时不要再死循环
            imgEl.src = FALLBACK_COVER;
        });
    };

    const NAMESPACES = {
        itunes: "http://www.itunes.com/dtds/podcast-1.0.dtd",
        media: "http://search.yahoo.com/mrss/",
        content: "http://purl.org/rss/1.0/modules/content/",
        dc: "http://purl.org/dc/elements/1.1/",
        atom: "http://www.w3.org/2005/Atom",
        googleplay: "http://www.google.com/schemas/play-podcasts/1.0",
        podcast: "https://podcastindex.org/namespace/1.0",
        psc: "http://podlove.org/simple-chapters",
        spotify: "http://www.spotify.com/ns/rss",
        sy: "http://purl.org/rss/1.0/modules/syndication/",
        slash: "http://purl.org/rss/1.0/modules/slash/",
        wfw: "http://wellformedweb.org/CommentAPI/",
        rawvoice: "http://www.rawvoice.com/rawvoiceRssModule/",
        feedburner: "http://rssnamespaces.org/feedburner/ext/1.0",
        creativeCommons: "http://backend.userland.com/creativeCommonsRssModule",
        source: "http://source.scripting.com/",
        omny: "https://omny.fm/rss-extensions"
    };

    const Bytes = {
        concat(a, b) {
            if (!a || a.length === 0) return b;
            if (!b || b.length === 0) return a;
            const out = new Uint8Array(a.length + b.length);
            out.set(a, 0);
            out.set(b, a.length);
            return out;
        },
        // 在字节流中查找 ASCII 子串。UTF-8 自同步，ASCII 字节不会出现在多字节序列中间，
        // 因此按字节查找标签边界是安全的（不依赖解码结果）。
        indexOf(buf, ascii, from = 0) {
            const pat = [];
            for (let i = 0; i < ascii.length; i++) pat.push(ascii.charCodeAt(i));
            const last = buf.length - pat.length;
            outer:
            for (let i = Math.max(0, from); i <= last; i++) {
                for (let j = 0; j < pat.length; j++) {
                    if (buf[i + j] !== pat[j]) continue outer;
                }
                return i;
            }
            return -1;
        }
    };

    const firstTag = (root, ...names) => {
        for (const name of names) {
            const list = root.getElementsByTagName(name);
            if (list && list.length) return list[0];
        }
        return null;
    };

    const childTag = (root, ...names) => {
        const lower = names.map(n => n.toLowerCase());
        for (const child of root.children) {
            const tag = (child.tagName || "").toLowerCase();
            if (lower.includes(tag)) return child;
        }
        return null;
    };

    const textOf = (el) => (el && el.textContent ? el.textContent.trim() : "");

    /* ---------- 应用 ---------- */

    const App = {
        state: {
            episodesMap: new Map(),
            renderedGuids: new Set(),
            filteredEpisodes: [],
            currentEpisode: null,
            sortNewestFirst: true,
            playbackRate: 1.0,
            rssUrl: "",
            pageSize: 20,

            chunkSize: 400 * 1024,
            headerChunkStep: 50 * 1024,

            totalContentLength: null,
            supportsRange: true,
            // 正向和反向分页各自独立结束,不能共用一个 "allLoaded":
            // 反向抓到字节 0 时整份文件已经从末尾覆盖到开头，
            // 这时两个方向都该视为结束；但正向自己抓到文件末尾时，
            // 并不代表反向也已经跑到过 0——两者不是同一件事。
            forwardDone: false,
            backwardDone: false,

            forwardNextStartByte: 0,
            backwardLastStartByte: null,

            forwardPendingItemStr: "",
            backwardPendingBytes: new Uint8Array(0),
            forwardDecoder: new TextDecoder("utf-8"),

            headerXmlSnippet: "",
            channelMeta: null,

            isLoadingChunk: false,
            isLoadingBatch: false,
            isSeeking: false,
            lastSaveAt: 0,
            progressData: {},

            playlistOpen: false,
            playlistCache: null,
            playlistLoading: false
        },

        $: {},
        observer: null,

        init() {
            this.cacheElements();
            this.state.progressData = this.readProgress();
            this.bindEvents();
            this.setupIntersectionObserver();
            this.loadPlaylist();   // 播放列表随时可能变化，页面一打开就去要最新的，不等用户点开抽屉

            const url = new URLSearchParams(window.location.search).get("url");
            if (!url) {
                this.showStatus("缺少播客地址。请在网址后附带 ?url=RSS 地址");
                return;
            }
            if (!/^https?:\/\//i.test(url)) {
                this.showStatus("播客地址无效，需要以 http:// 或 https:// 开头。");
                return;
            }

            this.state.rssUrl = url;
            this.loadFeed();
        },

        cacheElements() {
            [
                "statusView", "podcastHeader", "podcastCover", "podcastTitle",
                "podcastAuthor", "podcastDesc", "toolbar", "searchInput",
                "sortBtn", "episodeList", "playerBar", "mediaContainer",
                "mediaPlayer", "playerTitle", "playerSub", "playBtn", "rwBtn",
                "ffBtn", "rateBtn", "currentTime", "duration", "seekSlider", "loadMoreSentinel",
                "playlistToggleBtn", "playlistOverlay", "playlistDrawer", "playlistCloseBtn", "playlistBody", "homeBtn"
            ].forEach(id => this.$[id] = document.getElementById(id));
        },

        bindEvents() {
            const $ = this.$;

            let searchTimer = null;
            $.searchInput.addEventListener("input", () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => this.resetAndFilterEpisodes(), 200);
            });

            $.sortBtn.addEventListener("click", async () => {
                this.state.sortNewestFirst = !this.state.sortNewestFirst;
                $.sortBtn.textContent = this.state.sortNewestFirst ? "最新在前" : "最旧在前";
                this.resetAndFilterEpisodes();

                if (!this.state.sortNewestFirst && this.hasMoreBackward() && this.state.backwardLastStartByte === null) {
                    $.loadMoreSentinel.style.display = "block";
                    $.loadMoreSentinel.textContent = "正在从文件末尾读取最旧的单集…";
                    await this.fetchBackwardChunk();
                    this.resetAndFilterEpisodes();
                }
            });

            $.mediaContainer.addEventListener("click", () => this.requestVideoFullscreen());
            $.loadMoreSentinel.addEventListener("click", () => this.onReachBottom());

            $.homeBtn.addEventListener("click", () => { window.location.href = "/index"; });
            $.playlistToggleBtn.addEventListener("click", () => this.openPlaylistDrawer());
            $.playlistCloseBtn.addEventListener("click", () => this.closePlaylistDrawer());
            $.playlistOverlay.addEventListener("click", () => this.closePlaylistDrawer());
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && this.state.playlistOpen) this.closePlaylistDrawer();
            });

            let scrollTimer = null;
            window.addEventListener("scroll", () => {
                if (scrollTimer) return;
                scrollTimer = setTimeout(() => {
                    scrollTimer = null;
                    const doc = document.documentElement;
                    if (doc.scrollHeight - (window.scrollY || doc.scrollTop) - window.innerHeight < 400) {
                        this.onReachBottom();
                    }
                }, 150);
            }, { passive: true });

            // 滚动时连续（无极）缩小封面图，作者和简介按各自的滚动区间先后淡出/收起 —— 仅在手机端启用；
            // 电脑端不做任何滚动缩放动画（避免抖动），改用固定的紧凑头部样式（见 CSS 里的桌面媒体查询）
            const COVER_MAX = 120;
            const isDesktopLayout = () => window.matchMedia("(min-width: 600px)").matches;
            const PAD_MAX = 20, PAD_MIN = 10;
            const GAP_MAX = 15, GAP_MIN = 6;
            const MARGIN_MAX = 20, MARGIN_MIN = 10;
            const COLLAPSE_RANGE = 140; // 完全收起所需的滚动距离(px)
            const lerp = (a, b, t) => a + (b - a) * t;

            let authorFullHeight = null;
            let descFullHeight = null;
            this.measureHeaderCollapseHeights = () => {
                $.podcastAuthor.style.maxHeight = "";
                $.podcastDesc.style.maxHeight = "";
                authorFullHeight = $.podcastAuthor.scrollHeight;
                descFullHeight = $.podcastDesc.scrollHeight;
                updateHeaderCollapse();
            };

            const resetInlineCollapseStyles = () => {
                $.podcastCover.style.width = "";
                $.podcastCover.style.height = "";
                $.podcastCover.style.opacity = "";
                $.podcastCover.style.transform = "";
                $.podcastHeader.style.padding = "";
                $.podcastHeader.style.gap = "";
                $.podcastHeader.style.marginBottom = "";
                $.podcastAuthor.style.maxHeight = "";
                $.podcastAuthor.style.opacity = "";
                $.podcastAuthor.style.marginBottom = "";
                $.podcastDesc.style.maxHeight = "";
                $.podcastDesc.style.opacity = "";
            };

            let collapseTicking = false;
            const updateHeaderCollapse = () => {
                collapseTicking = false;

                if (isDesktopLayout()) {
                    // 电脑端：交给 CSS 的固定紧凑样式，清掉可能残留的内联样式即可
                    resetInlineCollapseStyles();
                    return;
                }

                const y = window.scrollY || document.documentElement.scrollTop;
                const progress = Math.min(1, Math.max(0, y / COLLAPSE_RANGE));

                // 作者先隐藏（0 ~ 0.4），简介随后隐藏（0.35 ~ 0.85），一项一项分开
                const authorProgress = Math.min(1, progress / 0.4);
                const descProgress = Math.min(1, Math.max(0, (progress - 0.35) / 0.5));

                const coverSize = lerp(COVER_MAX, 0, progress);
                $.podcastCover.style.width = coverSize + "px";
                $.podcastCover.style.height = coverSize + "px";
                $.podcastCover.style.transform = "";
                $.podcastCover.style.opacity = String(1 - progress);

                $.podcastHeader.style.padding = lerp(PAD_MAX, PAD_MIN, progress) + "px";
                $.podcastHeader.style.gap = lerp(GAP_MAX, GAP_MIN, progress) + "px";
                $.podcastHeader.style.marginBottom = lerp(MARGIN_MAX, MARGIN_MIN, progress) + "px";

                if (authorFullHeight !== null) {
                    $.podcastAuthor.style.maxHeight = authorFullHeight * (1 - authorProgress) + "px";
                    $.podcastAuthor.style.opacity = 1 - authorProgress;
                    $.podcastAuthor.style.marginBottom = (1 - authorProgress) * 8 + "px";
                }
                if (descFullHeight !== null) {
                    $.podcastDesc.style.maxHeight = descFullHeight * (1 - descProgress) + "px";
                    $.podcastDesc.style.opacity = 1 - descProgress;
                }
            };
            window.addEventListener("scroll", () => {
                if (collapseTicking) return;
                collapseTicking = true;
                requestAnimationFrame(updateHeaderCollapse);
            }, { passive: true });
            window.addEventListener("resize", updateHeaderCollapse, { passive: true });
            updateHeaderCollapse();


            $.playBtn.addEventListener("click", () => this.togglePlay());
            $.rwBtn.addEventListener("click", () => this.seekRelative(-15));
            $.ffBtn.addEventListener("click", () => this.seekRelative(15));
            $.rateBtn.addEventListener("click", () => this.changeRate());

            $.seekSlider.addEventListener("pointerdown", () => this.state.isSeeking = true);
            $.seekSlider.addEventListener("change", () => {
                this.applySeek();
                this.state.isSeeking = false;
            });
            $.seekSlider.addEventListener("input", () => {
                const dur = $.mediaPlayer.duration;
                if (isFinite(dur)) $.currentTime.textContent = this.formatTime(($.seekSlider.value / 1000) * dur);
            });

            $.mediaPlayer.addEventListener("timeupdate", () => {
                this.updateProgressUI();
                this.saveProgress(true);
            });
            $.mediaPlayer.addEventListener("ended", () => { this.saveProgress(); this.playNext(); });
            $.mediaPlayer.addEventListener("play", () => {
                $.playBtn.classList.add("playing");
                $.playBtn.title = "暂停";
                $.playBtn.setAttribute("aria-label", "暂停");
            });
            $.mediaPlayer.addEventListener("pause", () => {
                $.playBtn.classList.remove("playing");
                $.playBtn.title = "播放";
                $.playBtn.setAttribute("aria-label", "播放");
                this.saveProgress();
            });
            $.mediaPlayer.addEventListener("loadedmetadata", () => {
                this.restoreProgress();
                this.updateProgressUI();
            });
            $.mediaPlayer.addEventListener("error", () => {
                $.playerSub.textContent = "这一集无法播放，媒体地址可能已失效。";
            });

            window.addEventListener("pagehide", () => this.saveProgress());
            document.addEventListener("visibilitychange", () => { if (document.hidden) this.saveProgress(); });

            document.addEventListener("keydown", (e) => {
                if (["INPUT", "TEXTAREA"].includes(e.target.tagName) || e.target.isContentEditable) return;
                if (e.target.closest && e.target.closest("button")) return;
                if (e.code === "Space") { e.preventDefault(); this.togglePlay(); }
                if (e.code === "ArrowLeft") this.seekRelative(-5);
                if (e.code === "ArrowRight") this.seekRelative(5);
            });
        },

        setupIntersectionObserver() {
            this.observer = new IntersectionObserver((entries) => {
                if (entries[0].isIntersecting) this.onReachBottom();
            }, { root: null, rootMargin: "600px 0px", threshold: 0 });
            this.observer.observe(this.$.loadMoreSentinel);
        },

        /* ---------- 网络：字节级 Range ---------- */

        // 返回 { partial, bytes }。partial=false 表示服务器返回了整份文件（不支持 Range）。
        async fetchRange(start, end) {
            const options = { cache: "no-cache" };
            if (this.state.supportsRange) options.headers = { Range: `bytes=${start}-${end}` };

            const res = await fetch(this.state.rssUrl, options);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const bytes = new Uint8Array(await res.arrayBuffer());

            if (res.status === 206) {
                const range = res.headers.get("Content-Range");
                if (range && this.state.totalContentLength === null) {
                    const total = parseInt(range.split("/")[1], 10);
                    if (!isNaN(total)) this.state.totalContentLength = total;
                }
                return { partial: true, bytes };
            }

            // 200：服务器忽略或不支持 Range，拿到的是整份文件
            this.state.supportsRange = false;
            this.state.totalContentLength = bytes.length;
            return { partial: false, bytes };
        },

        async loadFeed() {
            try {
                await this.fetchHeaderThenFirstChunk();
            } catch (err) {
                console.error(err);
                this.showStatus(
                    "读取 RSS 失败：" + err.message +
                    "。常见原因是该地址未开放跨域访问（CORS），或没有暴露 Content-Range 响应头。"
                );
            }
        },

        // 从 0 字节开始按 50KB 递增，直到遇到第一个 <item> 为止，得到干净的 channel 头部。
        async fetchHeaderThenFirstChunk() {
            let accumulated = "";
            let start = 0;

            while (true) {
                const end = start + this.state.headerChunkStep - 1;
                const { partial, bytes } = await this.fetchRange(start, end);

                if (!partial) {
                    // 整份文件：一次性解析完，之后不再分片
                    const text = new TextDecoder("utf-8").decode(bytes);
                    const idx = text.search(/<item[\s>]/i);
                    this.state.headerXmlSnippet = idx !== -1 ? text.slice(0, idx) : text;
                    this.state.forwardDone = true;
                    this.state.backwardDone = true;
                    this.parseChannelMetadata();
                    if (idx !== -1) this.parseEpisodesFromText(text.slice(idx), false, true);
                    this.finishInitialLoad();
                    return;
                }

                accumulated += this.state.forwardDecoder.decode(bytes, { stream: true });
                start += bytes.length;                       // 用真实字节数推进指针，而不是字符数

                const idx = accumulated.search(/<item[\s>]/i);
                if (idx !== -1) {
                    this.state.headerXmlSnippet = accumulated.slice(0, idx);
                    this.state.forwardPendingItemStr = accumulated.slice(idx);
                    this.state.forwardNextStartByte = start;
                    // 文件小到刚好在这一轮里就被读到了末尾：正向、反向都已经没有更多字节
                    // 可读了，剩下这段 pending 文本会在下面的 fetchForwardChunk() 里被
                    // flushPendingForwardText() 当成最终数据解析掉。
                    if (this.state.totalContentLength !== null && start >= this.state.totalContentLength) {
                        this.state.forwardDone = true;
                        this.state.backwardDone = true;
                    }
                    break;
                }

                const reachedEnd = bytes.length === 0 ||
                    (this.state.totalContentLength !== null && start >= this.state.totalContentLength);
                if (reachedEnd) {
                    this.state.headerXmlSnippet = accumulated;
                    this.state.forwardNextStartByte = start;
                    this.state.forwardDone = true;
                    this.state.backwardDone = true;
                    break;
                }
            }

            this.parseChannelMetadata();
            await this.fetchForwardChunk();
            this.finishInitialLoad();
        },

        finishInitialLoad() {
            this.updateFilteredEpisodes();
            this.loadNextBatch();
        },

        // 首个分片有没有单集，不能代表整份文件有没有单集——像视频节目常常单集体积很大
        // （较长的简介、封面、多个 enclosure），一个分片里可能连一条完整的 <item> 都凑不齐，
        // 需要再抓一两个分片才能拼出第一条。所以“没有找到单集”只在正向、反向都已经
        // 抓到头（再也没有更多字节可读）却仍然一条都没解析出来时才提示；
        // 只要后续任何一次分片解析出了单集，这里也会把提示收起去。
        refreshEmptyStatus() {
            if (this.state.episodesMap.size > 0) {
                this.$.statusView.style.display = "none";
                return;
            }
            if (!this.hasMoreForward() && !this.hasMoreBackward()) {
                this.showStatus("这个地址里没有找到可播放的单集。");
            } else {
                this.$.statusView.style.display = "none";
            }
        },

        /* ---------- XML 拼装与解析 ---------- */

        // 分片得到的 <item> 里常带 itunes:/media: 等前缀。XML 解析器遇到未声明的前缀会直接报错，
        // 所以在根元素上补齐常见命名空间声明。
        ensureNamespaces(header) {
            let snippet = (header || "").trim();

            const closeIdx = snippet.toLowerCase().lastIndexOf("</channel>");
            if (closeIdx !== -1) snippet = snippet.slice(0, closeIdx);

            if (!/<rss[\s>]/i.test(snippet)) {
                const decls = Object.entries(NAMESPACES).map(([p, u]) => `xmlns:${p}="${u}"`).join(" ");
                return `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" ${decls}><channel>`;
            }

            return snippet.replace(/<rss\b([^>]*)>/i, (match, attrs) => {
                let extra = "";
                for (const [prefix, uri] of Object.entries(NAMESPACES)) {
                    if (!new RegExp(`xmlns:${prefix}\\s*=`, "i").test(attrs)) extra += ` xmlns:${prefix}="${uri}"`;
                }
                return `<rss${attrs}${extra}>`;
            });
        },

        buildXml(itemsStr) {
            return `${this.ensureNamespaces(this.state.headerXmlSnippet)}\n${itemsStr}\n</channel>\n</rss>`;
        },

        parseXml(str) {
            const doc = new DOMParser().parseFromString(str, "application/xml");
            return doc.getElementsByTagName("parsererror").length ? null : doc;
        },

        parseChannelMetadata() {
            const doc = this.parseXml(this.buildXml(""));
            const channel = doc && doc.getElementsByTagName("channel")[0];
            if (!channel) return;

            const image = channel.getElementsByTagName("image")[0];
            const itunesImage = firstTag(channel, "itunes:image");
            const cover = (itunesImage && itunesImage.getAttribute("href")) ||
                          textOf(image && childTag(image, "url")) || "";

            this.state.channelMeta = {
                title: textOf(childTag(channel, "title")) || "未命名播客",
                author: textOf(childTag(channel, "itunes:author")) || textOf(childTag(channel, "author")) ||
                        textOf(childTag(channel, "managingEditor")),
                desc: (textOf(childTag(channel, "description")) || textOf(childTag(channel, "itunes:summary"))).slice(0, 300),
                image: cover
            };

            this.$.podcastTitle.textContent = this.state.channelMeta.title;
            this.$.podcastAuthor.textContent = this.state.channelMeta.author;
            this.$.podcastDesc.textContent = this.state.channelMeta.desc;
            withCoverFallback(this.$.podcastCover);
            this.$.podcastCover.src = cover || FALLBACK_COVER;
            document.title = this.state.channelMeta.title;

            this.$.statusView.style.display = "none";
            this.$.podcastHeader.style.display = "flex";
            this.$.toolbar.style.display = "flex";
            if (this.measureHeaderCollapseHeights) this.measureHeaderCollapseHeights();
        },

        /* ---------- 分片抓取 ---------- */

        hasMoreForward() {
            if (this.state.forwardDone) return false;
            if (this.state.totalContentLength === null) return true;
            return this.state.forwardNextStartByte < this.state.totalContentLength;
        },

        hasMoreBackward() {
            // 反向分页与正向指针完全独立：从文件末尾开始，
            // 把上一次切片的起始字节作为这一次的结束字节，逐段向文件开头推进，
            // 直到某次切片的起始字节落到 0 为止（此时整份文件已从末尾覆盖到开头）。
            // 这里不应该跟 forwardNextStartByte 比较——那样会在与正向已读区间
            // 相遇时就提前判定"没有更多"，导致文件靠前的一批 item 永远抓不到。
            if (this.state.backwardDone || !this.state.supportsRange) return false;
            if (this.state.totalContentLength === null) return false;
            if (this.state.backwardLastStartByte === null) return true;
            return this.state.backwardLastStartByte > 0;
        },

        // 返回本次新增的单集数量
        // 没有更多字节可读了，但上一次切片末尾可能还留着一截没解析的 <item> 文本
        // （最典型的情况：文件小到刚好在“找 header 边界”那一轮读取里就已经整份读完了，
        // 此后不会再有任何一次正向抓取），必须在这里把它当作最终数据处理掉，
        // 否则这些单集会一直沉在 forwardPendingItemStr 里，永远不会显示出来。
        flushPendingForwardText() {
            const pending = this.state.forwardPendingItemStr;
            this.state.forwardPendingItemStr = "";
            if (!pending) return 0;
            const before = this.state.episodesMap.size;
            this.parseEpisodesFromText(pending, false, true);
            return this.state.episodesMap.size - before;
        },

        async fetchForwardChunk() {
            if (this.state.isLoadingChunk) return 0;
            if (!this.hasMoreForward()) return this.flushPendingForwardText();

            this.state.isLoadingChunk = true;
            const before = this.state.episodesMap.size;

            try {
                const start = this.state.forwardNextStartByte;
                let end = start + this.state.chunkSize - 1;
                if (this.state.totalContentLength !== null) {
                    end = Math.min(end, this.state.totalContentLength - 1);
                }
                if (end < start) {
                    this.state.forwardDone = true;
                    this.flushPendingForwardText();
                    return this.state.episodesMap.size - before;
                }

                const { partial, bytes } = await this.fetchRange(start, end);

                if (!partial) {
                    this.state.forwardDone = true;
                    this.state.backwardDone = true;
                    // 服务器给的是整份文件（不是我们请求的那个字节区间），
                    // 之前残留的 forwardPendingItemStr 是从某个字节偏移量截出来的片段，
                    // 拼到完整全文前面反而会重复/错位，直接丢弃，只解析这份完整文本。
                    this.state.forwardPendingItemStr = "";
                    this.parseEpisodesFromText(new TextDecoder("utf-8").decode(bytes), false, true);
                } else {
                    this.state.forwardNextStartByte = start + bytes.length;
                    if (bytes.length === 0) this.state.forwardDone = true;

                    const text = this.state.forwardPendingItemStr +
                                 this.state.forwardDecoder.decode(bytes, { stream: true });
                    this.state.forwardPendingItemStr = "";
                    this.parseEpisodesFromText(text, false, !this.hasMoreForward());
                    if (!this.hasMoreForward()) this.flushPendingForwardText();
                }
            } catch (err) {
                console.warn("正向抓取失败：", err);
                this.state.forwardDone = true;
            } finally {
                this.state.isLoadingChunk = false;
            }

            return this.state.episodesMap.size - before;
        },

        // 反向反推：上一次切片的起始字节，就是这一次切片的结束字节；
        // 首次调用时结束字节是文件末尾（totalContentLength - 1）。
        // 如此逐段向文件开头推进，直到某次切片的起始字节落到 0。
        async fetchBackwardChunk() {
            if (this.state.isLoadingChunk || !this.hasMoreBackward()) return 0;

            this.state.isLoadingChunk = true;
            const before = this.state.episodesMap.size;

            try {
                const end = this.state.backwardLastStartByte === null
                    ? this.state.totalContentLength - 1
                    : this.state.backwardLastStartByte - 1;
                if (end < 0) {
                    this.state.backwardDone = true;
                    return 0;
                }

                const start = Math.max(0, end - this.state.chunkSize + 1);
                const { partial, bytes } = await this.fetchRange(start, end);

                if (!partial) {
                    // 服务器中途不再支持 Range，只能拿到整份文件；两个方向都算读完了
                    this.state.forwardDone = true;
                    this.state.backwardDone = true;
                    this.parseEpisodesFromText(new TextDecoder("utf-8").decode(bytes), false, true);
                    return this.state.episodesMap.size - before;
                }

                this.state.backwardLastStartByte = start;

                // 上一次（更靠后的）切片开头那截残缺 item，接在这次切片的末尾
                const combined = Bytes.concat(bytes, this.state.backwardPendingBytes);

                // 在字节层面切掉开头的残缺 item，避免解码出半个 UTF-8 字符。
                // 如果这次切片本身就是文件开头（start===0），没有更前面的内容可以拼接，
                // 不需要再暂存任何残缺片段。
                let cut = 0;
                if (start > 0) {
                    const openIdx = Bytes.indexOf(combined, "<item");
                    const closeIdx = Bytes.indexOf(combined, "</item>");
                    if (closeIdx !== -1 && (openIdx === -1 || closeIdx < openIdx)) cut = closeIdx + 7;
                    else if (openIdx > 0) cut = openIdx;
                }
                this.state.backwardPendingBytes = combined.slice(0, cut);

                const text = new TextDecoder("utf-8").decode(combined.slice(cut));
                this.parseEpisodesFromText(text, true, true);

                // 起始字节已经到达文件开头：反向已经把整份文件从末尾覆盖到开头，
                // 正向也没有新东西可抓了。
                if (start === 0) {
                    this.state.backwardDone = true;
                    this.state.forwardDone = true;
                }
            } catch (err) {
                console.warn("反向抓取失败：", err);
                this.state.backwardDone = true;
            } finally {
                this.state.isLoadingChunk = false;
            }

            return this.state.episodesMap.size - before;
        },

        // isFinal 为 true 时不再暂存尾部残缺内容（已经是流的末尾）
        parseEpisodesFromText(text, isBackward, isFinal) {
            let working = text;

            if (!isBackward && !isFinal) {
                const lastOpen = working.toLowerCase().lastIndexOf("<item");
                const lastClose = working.toLowerCase().lastIndexOf("</item>");
                if (lastOpen !== -1 && lastOpen > lastClose) {
                    this.state.forwardPendingItemStr = working.slice(lastOpen);
                    working = working.slice(0, lastOpen);
                }
            }

            const matches = working.match(/<item[\s>][\s\S]*?<\/item>/gi);
            if (!matches || !matches.length) return;

            const doc = this.parseXml(this.buildXml(matches.join("\n")));
            if (!doc) {
                // 整批解析失败时退回逐条解析，避免一条坏数据吃掉整个切片
                matches.forEach(one => {
                    const single = this.parseXml(this.buildXml(one));
                    if (single) this.mergeEpisodes(single, isBackward);
                });
                return;
            }
            this.mergeEpisodes(doc, isBackward);
        },

        // 文件中间是否还有一段字节完全没读过：某次反向抓取已经发生过，
        // 但正向指针还没有推进到与它相接的位置。只要这段空隙存在，
        // 空隙两侧各自读到的单集就不能保证是全局连续有序的——
        // 空隙对面那一端的批次可能实际上该排在空隙被填满之后，
        // 而不是紧跟在当前已读到的这一端后面。
        hasGap() {
            return this.state.backwardLastStartByte !== null &&
                   this.state.forwardNextStartByte < this.state.backwardLastStartByte;
        },

        mergeEpisodes(doc, isBackward) {
            const channel = doc.getElementsByTagName("channel")[0];
            if (!channel) return;

            const fallbackImage = (this.state.channelMeta && this.state.channelMeta.image) || "";
            const origin = isBackward ? "backward" : "forward";

            for (const item of channel.getElementsByTagName("item")) {
                const enclosure = childTag(item, "enclosure");
                const mediaContent = firstTag(item, "media:content");
                const mediaUrl = (enclosure && enclosure.getAttribute("url")) ||
                                 (mediaContent && mediaContent.getAttribute("url")) || "";
                if (!mediaUrl) continue;

                const guid = textOf(childTag(item, "guid")) || mediaUrl;
                if (this.state.episodesMap.has(guid)) continue;

                const type = (enclosure && enclosure.getAttribute("type")) ||
                             (mediaContent && mediaContent.getAttribute("type")) || "";
                const isVideo = type.startsWith("video/") || /\.(mp4|m4v|webm|mov)(\?|#|$)/i.test(mediaUrl);

                const itunesImage = firstTag(item, "itunes:image");
                const itemImage = (itunesImage && itunesImage.getAttribute("href")) || fallbackImage;

                const pubDate = textOf(childTag(item, "pubDate"));
                const parsed = pubDate ? Date.parse(pubDate) : NaN;

                this.state.episodesMap.set(guid, {
                    guid,
                    title: textOf(childTag(item, "title")) || "未命名单集",
                    date: isNaN(parsed) ? 0 : parsed,     // 缺少 pubDate 时记为 0，而不是被 Date.parse("0") 解析成 2000 年
                    url: mediaUrl,
                    image: itemImage,
                    isVideo,
                    origin      // 'forward'（从文件头部读到）或 'backward'（从文件尾部反推读到）
                });
            }

            this.updateFilteredEpisodes();
        },

        /* ---------- 列表渲染 ---------- */

        updateFilteredEpisodes() {
            const query = this.$.searchInput.value.trim().toLowerCase();
            let all = Array.from(this.state.episodesMap.values());

            if (this.hasGap()) {
                // 空隙还没填上：只展示与当前浏览方向一致来源的单集，
                // 把空隙对面那一端已经读到、但顺序还不能确定的单集先按下不表。
                // 等反向抓取追上正向指针（空隙消失），它们才会一次性正确地
                // 出现在真正该在的位置——通常就是列表最底部。
                const excludeOrigin = this.state.sortNewestFirst ? "backward" : "forward";
                all = all.filter(ep => ep.origin !== excludeOrigin);
            }

            this.state.filteredEpisodes = (query
                ? all.filter(ep => ep.title.toLowerCase().includes(query))
                : all
            ).sort((a, b) => this.state.sortNewestFirst ? b.date - a.date : a.date - b.date);

            this.refreshEmptyStatus();
        },

        resetAndFilterEpisodes() {
            this.$.episodeList.innerHTML = "";
            this.state.renderedGuids.clear();
            this.updateFilteredEpisodes();
            this.loadNextBatch();
        },

        pendingRenderCount() {
            let n = 0;
            for (const ep of this.state.filteredEpisodes) {
                if (!this.state.renderedGuids.has(ep.guid)) n++;
            }
            return n;
        },

        createEpisodeNode(ep) {
            const node = document.createElement("div");
            node.className = "episode-item";
            node.tabIndex = 0;
            node.dataset.guid = ep.guid;

            const cover = document.createElement("img");
            cover.className = "episode-cover";
            cover.loading = "lazy";
            cover.referrerPolicy = "no-referrer";
            cover.alt = "";
            withCoverFallback(cover);
            cover.src = ep.image || FALLBACK_COVER;

            const content = document.createElement("div");
            content.className = "episode-content";

            const title = document.createElement("div");
            title.className = "episode-title";
            title.textContent = ep.title;          // 用 textContent，标题里的 HTML 不会被当成标记执行
            if (ep.isVideo) {
                const badge = document.createElement("span");
                badge.className = "badge";
                badge.textContent = "视频";
                title.appendChild(badge);
            }

            const meta = document.createElement("div");
            meta.className = "episode-meta";
            meta.textContent = ep.date ? new Date(ep.date).toLocaleDateString() : "";

            content.append(title, meta);
            node.append(cover, content);

            const saved = this.state.progressData[ep.guid];
            const percent = saved && saved.duration ? (saved.time / saved.duration) * 100 : 0;
            if (percent > 0) node.appendChild(this.createProgressBar(percent));

            node.addEventListener("click", () => this.playEpisode(ep));
            node.addEventListener("keydown", (e) => {
                if (e.key === "Enter") this.playEpisode(ep);
            });
            return node;
        },

        createProgressBar(percent) {
            const bg = document.createElement("div");
            bg.className = "progress-bar-bg";
            const fill = document.createElement("div");
            fill.className = "progress-bar-fill";
            fill.style.width = Math.min(100, percent) + "%";
            bg.appendChild(fill);
            return bg;
        },

        loadNextBatch() {
            const fragment = document.createDocumentFragment();
            let added = 0;

            for (const ep of this.state.filteredEpisodes) {
                if (added >= this.state.pageSize) break;
                if (this.state.renderedGuids.has(ep.guid)) continue;
                fragment.appendChild(this.createEpisodeNode(ep));
                this.state.renderedGuids.add(ep.guid);
                added++;
            }

            this.$.episodeList.appendChild(fragment);
            this.updateSentinel();
            return added;
        },

        updateSentinel() {
            const more = this.pendingRenderCount() > 0 ||
                         (this.state.sortNewestFirst ? this.hasMoreForward() : (this.hasMoreBackward() || this.hasMoreForward()));
            if (more) {
                this.$.loadMoreSentinel.style.display = "block";
                this.$.loadMoreSentinel.textContent = "加载更多（也可点这里手动加载）";
            } else {
                this.$.loadMoreSentinel.style.display = "none";
            }
        },

        async onReachBottom() {
            if (this.state.isLoadingBatch) return;
            this.state.isLoadingBatch = true;

            try {
                if (this.pendingRenderCount() > 0) {
                    this.loadNextBatch();
                    return;
                }

                const canFetch = this.state.sortNewestFirst
                    ? this.hasMoreForward()
                    : (this.hasMoreBackward() || this.hasMoreForward());

                if (!canFetch) {
                    this.updateSentinel();
                    return;
                }

                this.$.loadMoreSentinel.style.display = "block";
                this.$.loadMoreSentinel.textContent = this.state.sortNewestFirst
                    ? "正在加载更多单集…"
                    : "正在从文件末尾向前读取…";

                if (this.state.sortNewestFirst) await this.fetchForwardChunk();
                else await this.fetchBackwardChunk();

                if (this.pendingRenderCount() > 0) this.loadNextBatch();
                else this.updateSentinel();
            } finally {
                this.state.isLoadingBatch = false;
            }
        },

        /* ---------- 播放 ---------- */

        playEpisode(ep) {
            this.saveProgress();
            this.state.currentEpisode = ep;

            const $ = this.$;
            $.playerTitle.textContent = ep.title;
            $.playerSub.textContent = ep.isVideo ? "视频节目" : "音频节目";
            $.playerBar.classList.add("active");
            $.mediaContainer.classList.toggle("video-mode", !!ep.isVideo);

            $.episodeList.querySelectorAll(".episode-item.playing").forEach(n => n.classList.remove("playing"));
            const node = $.episodeList.querySelector(`[data-guid="${CSS.escape(ep.guid)}"]`);
            if (node) node.classList.add("playing");

            $.mediaPlayer.src = ep.url;
            $.mediaPlayer.playbackRate = this.state.playbackRate;
            $.mediaPlayer.play().catch(() => {});

            this.updateMediaSession(ep);
        },

        togglePlay() {
            const player = this.$.mediaPlayer;
            if (!player.src) return;
            if (player.paused) player.play().catch(() => {});
            else player.pause();
        },

        seekRelative(secs) {
            const player = this.$.mediaPlayer;
            if (!isFinite(player.duration)) return;
            player.currentTime = Math.max(0, Math.min(player.duration, player.currentTime + secs));
        },

        applySeek() {
            const player = this.$.mediaPlayer;
            if (!isFinite(player.duration)) return;
            player.currentTime = (this.$.seekSlider.value / 1000) * player.duration;
        },

        changeRate() {
            const rates = [0.75, 1.0, 1.25, 1.5, 2.0];
            const idx = rates.indexOf(this.state.playbackRate);
            this.state.playbackRate = rates[(idx + 1) % rates.length];
            this.$.mediaPlayer.playbackRate = this.state.playbackRate;   // 立即生效，而不是等下一集
            this.$.rateBtn.textContent = `${this.state.playbackRate.toFixed(2).replace(/0$/, "")}x`;
        },

        requestVideoFullscreen() {
            const video = this.$.mediaPlayer;
            if (!video || !this.state.currentEpisode || !this.state.currentEpisode.isVideo) return;
            if (video.requestFullscreen) video.requestFullscreen().catch(() => {});
            else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
            else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
        },

        /* ---------- 播放列表切换 ---------- */

        openPlaylistDrawer() {
            this.state.playlistOpen = true;
            this.$.playlistDrawer.classList.add("active");
            this.$.playlistOverlay.classList.add("active");
            this.$.playlistDrawer.setAttribute("aria-hidden", "false");
            this.loadPlaylist();   // 列表随时会变，每次打开都重新要一份最新的，不用缓存
        },

        closePlaylistDrawer() {
            this.state.playlistOpen = false;
            this.$.playlistDrawer.classList.remove("active");
            this.$.playlistOverlay.classList.remove("active");
            this.$.playlistDrawer.setAttribute("aria-hidden", "true");
        },

        async loadPlaylist() {
            if (this.state.playlistLoading) return;
            this.state.playlistLoading = true;

            const $ = this.$;
            $.playlistBody.innerHTML = "";
            const status = document.createElement("div");
            status.className = "playlist-status";
            status.textContent = "正在加载列表…";
            $.playlistBody.appendChild(status);

            try {
                const res = await fetch("/playlist", { cache: "no-cache" });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                const dict = await res.json();
                if (!dict || typeof dict !== "object" || Array.isArray(dict)) {
                    throw new Error("返回的不是一个 名称→地址 的字典");
                }

                this.state.playlistCache = dict;
                this.renderPlaylist(dict);
            } catch (err) {
                console.warn("加载播放列表失败：", err);
                this.renderPlaylistError(err.message);
            } finally {
                this.state.playlistLoading = false;
            }
        },

        renderPlaylist(dict) {
            const $ = this.$;
            $.playlistBody.innerHTML = "";

            const names = Object.keys(dict);
            if (names.length === 0) {
                const empty = document.createElement("div");
                empty.className = "playlist-status";
                empty.textContent = "列表是空的。";
                $.playlistBody.appendChild(empty);
                return;
            }

            const fragment = document.createDocumentFragment();
            names.forEach(name => {
                const url = dict[name];
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "playlist-item";
                btn.textContent = name;    // 用 textContent，字典里的名字不会被当成 HTML 解析
                if (typeof url === "string" && url === this.state.rssUrl) btn.classList.add("active");
                btn.addEventListener("click", () => this.switchFeed(url));
                fragment.appendChild(btn);
            });
            $.playlistBody.appendChild(fragment);
        },

        renderPlaylistError(message) {
            const $ = this.$;
            $.playlistBody.innerHTML = "";

            const status = document.createElement("div");
            status.className = "playlist-status";
            status.textContent = "列表刷新失败：" + message +
                (this.state.playlistCache ? "（下面显示的是上一次成功获取的列表）" : "");
            $.playlistBody.appendChild(status);

            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "btn playlist-retry-btn";
            retry.textContent = "重试";
            retry.addEventListener("click", () => this.loadPlaylist());
            $.playlistBody.appendChild(retry);

            // 这次刷新失败了，但如果之前成功拿到过一份，仍然把它显示出来，
            // 好过什么都点不了——列表本身随时可能变，用户仍然可以选一个旧条目试试。
            if (this.state.playlistCache) {
                const stale = document.createElement("div");
                Object.keys(this.state.playlistCache).forEach(name => {
                    const url = this.state.playlistCache[name];
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "playlist-item";
                    btn.textContent = name;
                    if (typeof url === "string" && url === this.state.rssUrl) btn.classList.add("active");
                    btn.addEventListener("click", () => this.switchFeed(url));
                    stale.appendChild(btn);
                });
                $.playlistBody.appendChild(stale);
            }
        },

        switchFeed(url) {
            if (!url || typeof url !== "string") return;
            if (url === this.state.rssUrl) {
                this.closePlaylistDrawer();
                return;
            }
            // 整个应用的状态（分片指针、已知单集、播放进度等）都是围着当前这份 RSS 建立起来的，
            // 直接带上新的 ?url= 刷新页面、从头走一遍初始化，比在原地重置一大堆内部状态更可靠。
            window.location.href = `${window.location.pathname}?url=${encodeURIComponent(url)}`;
        },

        updateProgressUI() {
            const player = this.$.mediaPlayer;
            if (!isFinite(player.duration) || player.duration === 0) return;

            this.$.duration.textContent = this.formatTime(player.duration);
            if (this.state.isSeeking) return;

            this.$.currentTime.textContent = this.formatTime(player.currentTime);
            this.$.seekSlider.value = Math.round((player.currentTime / player.duration) * 1000);
        },

        /* ---------- 进度存储 ---------- */

        readProgress() {
            try {
                return JSON.parse(localStorage.getItem("podcast_progress") || "{}");
            } catch (e) {
                return {};
            }
        },

        saveProgress(throttled = false) {
            const ep = this.state.currentEpisode;
            const player = this.$.mediaPlayer;
            if (!ep || !isFinite(player.duration) || player.duration === 0) return;

            const now = Date.now();
            if (throttled && now - this.state.lastSaveAt < 5000) return;
            this.state.lastSaveAt = now;

            this.state.progressData[ep.guid] = {
                time: player.currentTime,
                duration: player.duration,
                updated: now
            };

            try {
                localStorage.setItem("podcast_progress", JSON.stringify(this.state.progressData));
            } catch (e) {
                console.warn("进度无法写入本地存储：", e);
            }

            this.updateEpisodeProgressBar(ep.guid, (player.currentTime / player.duration) * 100);
        },

        updateEpisodeProgressBar(guid, percent) {
            const node = this.$.episodeList.querySelector(`[data-guid="${CSS.escape(guid)}"]`);
            if (!node) return;
            let fill = node.querySelector(".progress-bar-fill");
            if (!fill) {
                node.appendChild(this.createProgressBar(percent));
                return;
            }
            fill.style.width = Math.min(100, percent) + "%";
        },

        restoreProgress() {
            const ep = this.state.currentEpisode;
            if (!ep) return;
            const saved = this.state.progressData[ep.guid];
            if (saved && saved.time < saved.duration - 5) {
                this.$.mediaPlayer.currentTime = saved.time;
            }
        },

        playNext() {
            const list = this.state.filteredEpisodes;
            const idx = list.findIndex(e => this.state.currentEpisode && e.guid === this.state.currentEpisode.guid);
            if (idx >= 0 && idx < list.length - 1) this.playEpisode(list[idx + 1]);
        },

        playPrevious() {
            const list = this.state.filteredEpisodes;
            const idx = list.findIndex(e => this.state.currentEpisode && e.guid === this.state.currentEpisode.guid);
            if (idx > 0) this.playEpisode(list[idx - 1]);
        },

        updateMediaSession(ep) {
            if (!("mediaSession" in navigator)) return;

            navigator.mediaSession.metadata = new MediaMetadata({
                title: ep.title,
                artist: (this.state.channelMeta && this.state.channelMeta.author) || "",
                album: (this.state.channelMeta && this.state.channelMeta.title) || "",
                artwork: ep.image ? [{ src: ep.image, sizes: "512x512" }] : []
            });

            const set = (action, handler) => {
                try { navigator.mediaSession.setActionHandler(action, handler); } catch (e) {}
            };
            set("play", () => this.$.mediaPlayer.play().catch(() => {}));
            set("pause", () => this.$.mediaPlayer.pause());
            set("seekbackward", () => this.seekRelative(-15));
            set("seekforward", () => this.seekRelative(15));
            set("previoustrack", () => this.playPrevious());
            set("nexttrack", () => this.playNext());
        },

        formatTime(secs) {
            if (!isFinite(secs) || secs < 0) return "0:00";
            const total = Math.floor(secs);
            const h = Math.floor(total / 3600);
            const m = Math.floor((total % 3600) / 60);
            const s = total % 60;
            const pad = n => (n < 10 ? "0" + n : String(n));
            return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
        },

        showStatus(msg) {
            this.$.statusView.textContent = msg;
            this.$.statusView.style.display = "block";
        }
    };

    document.addEventListener("DOMContentLoaded", () => App.init());
})();