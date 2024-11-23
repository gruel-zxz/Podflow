SELECT
    txn_dt as '交易日期',
    txn_time as '交易时间',
    biz_org as '营业机构',
    acct_org as '帐务机构',
    channel_type_id as '渠道类型编号',
    txn_channel as '交易渠道',
    biz_cd as '业务代号',
    currency_cd as '币种代码',
    subject_cd as '科目号',
    subject_store_cd as '科目存储代码',
    txn_cd as '交易代码',
    acctno as '账号',
    dr_or_ind as '借贷标志',
    txn_amt as '交易金额',
    acct_bal as '账户余额',
    cust_acctno as '客户账号',
    cust_acctno_type_cd as '客户账号类型代码',
    abstract_cd as '摘要代码',
    abstract_cd2 as '摘要代码 2',
    cust_id as '客户号',
    acct_chinese_name as '账户中文名',
    evt_stat_cd as '事件状态',
    opposite_acctno as '对方账号',
    opposite_acct_name as '对方户名',
    opposite_bank_id as '对方行号',
    opposite_bank_name as '对方行名',
    oppo_remark_inf as '对手备注信息',
    oppo_src_sys as '对手来源系统',
    ROW_NUMBER() OVER(PARTITION BY t.acctno ORDER BY t.txn_dt DESC, t.txn_time DESC) AS rn
FROM MTC_VIEW.HDS_DY90_TXN_OPPO t
WHERE t.pt_dt BETWEEN '2011-01-01' AND '2025-11-20'
    AND t.TXN_DT BETWEEN '20120101' AND '20241120'
    AND t.txn_cd <> '9786'
    AND t.txn_cd <> '7997'
    AND t.acctno IN ('0987654321', '1234567890')
ORDER BY txn_dt, txn_time;