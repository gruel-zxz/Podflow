# podflow/config/channge_icon.py
# coding: utf-8

from datetime import datetime, timedelta, timezone
from astral import LocationInfo
from astral.sun import sun
from podflow.basic.http_client import http_client
from podflow.basic.write_log import write_log
from podflow import gVar, default_config


# 获取日出日落并判断昼夜模块
def http_day_and_night(latitude, longitude):
    sun_url = "https://api.sunrise-sunset.org/json"
    sun_data = {
        "lat": latitude,
        "lng": longitude,
        "date": "today",
    }
    sunrise_sunset = http_client(sun_url, "获取日出日落", 3, 5, True, None, sun_data)
    if not sunrise_sunset:
        return None
    try:
        time_dict = sunrise_sunset.json()["results"]
        sunrise = time_dict["sunrise"]
        sunset = time_dict["sunset"]
    except KeyError:
        return None
    # 获取当前时间, 并去除时区
    now = datetime.now()
    # 将日出和日落时间转换为datetime对象
    today = now.date()
    sunrise_time = datetime.strptime(sunrise, "%I:%M:%S %p")
    sunrise_time = sunrise_time.replace(
        year=today.year, month=today.month, day=today.day, tzinfo=timezone.utc
    )
    sunset_time = datetime.strptime(sunset, "%I:%M:%S %p")
    sunset_time = sunset_time.replace(
        year=today.year, month=today.month, day=today.day, tzinfo=timezone.utc
    )
    # 转换日出和日落时间为时间戳
    sunrise_now = sunrise_time.timestamp()
    sunset_now = sunset_time.timestamp()
    today = now.timestamp()
    # 计算昨天及明天日出和日落时间戳
    sunrise_yesterday = sunrise_now - 3600 * 24
    sunset_yesterday = sunset_now - 3600 * 24
    sunrise_tommorrow = sunrise_now + 3600 * 24
    sunset_tommorrow = sunset_now + 3600 * 24
    if sunrise_now < sunset_now:
        return (
            "light"
            if (
                sunrise_now < today < sunset_now
                or sunrise_yesterday < today < sunset_yesterday
                or sunrise_tommorrow < today < sunset_tommorrow
            )
            else "dark"
        )
    if (
        sunrise_now > today > sunset_now
        or sunrise_yesterday > today > sunset_yesterday
        or sunrise_tommorrow > today > sunset_tommorrow
    ):
        return "dark"
    else:
        return "light"


# 根据经纬度判断昼夜模块
def judging_day_and_night(latitude, longitude):
    # 创建一个 LocationInfo 对象, 只提供经纬度信息
    location = LocationInfo("", "", "", latitude=latitude, longitude=longitude)
    # 获取当前日期和时间, 并为其添加时区信息
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    tommorrow = now + timedelta(days=1)

    def sunrise_sunset(time):
        # 创建一个 Sun 对象
        sun_time = sun(location.observer, date=time)
        # 计算日出和日落时间, 以及日落前和日出后的一小时
        sunrise = sun_time["sunrise"]
        sunset = sun_time["sunset"]
        sunrise_minus_one_hour = sunrise  # - timedelta(hours=1)
        sunset_plus_one_hour = sunset  # + timedelta(hours=1)
        return sunrise_minus_one_hour, sunset_plus_one_hour

    sunrise_now, sunset_now = sunrise_sunset(now)
    sunrise_yesterday, sunset_yesterday = sunrise_sunset(yesterday)
    sunrise_tommorrow, sunset_tommorrow = sunrise_sunset(tommorrow)
    if sunrise_now < sunset_now:
        return (
            "light"
            if (
                sunrise_now < now < sunset_now
                or sunrise_yesterday < now < sunset_yesterday
                or sunrise_tommorrow < now < sunset_tommorrow
            )
            else "dark"
        )
    if (
        sunrise_now > now > sunset_now
        or sunrise_yesterday > now > sunset_yesterday
        or sunrise_tommorrow > now > sunset_tommorrow
    ):
        return "dark"
    else:
        return "light"


def ipinfo():
    if response := http_client("https://ipinfo.io/json/", "", 1, 0):
        data = response.json()
        # 提取经度和纬度
        coordinates = data["loc"].split(",")
        return True, coordinates[0], coordinates[1]
    else:
        return False, None, None


def ipapi():
    if response := http_client("http://ip-api.com/json/", "", 1, 0):
        data = response.json()
        # 提取经度和纬度
        return True, data["lat"], data["lon"]
    else:
        return False, None, None


def freegeoip():
    if response := http_client("https://freegeoip.app/json/", "", 1, 0):
        data = response.json()
        # 提取经度和纬度
        return True, data["latitude"], data["longitude"]
    else:
        return False, None, None


# 根据日出日落修改封面(只适用原封面)模块
def channge_icon():
    config = gVar.config
    if config["icon"] != default_config["icon"]:
        return
    label = False
    # 公网获取经纬度
    label, latitude, longitude = ipinfo()
    if label is False:
        write_log("获取经纬度信息重试中...\033[97m1\033[0m")
        label, latitude, longitude = ipapi()
    if label is False:
        write_log("获取经纬度信息重试中...\033[97m2\033[0m")
        label, latitude, longitude = freegeoip()
    if label is False:
        write_log("获取经纬度信息失败")
    if label:
        picture_name = http_day_and_night(latitude, longitude)
        if not picture_name:
            write_log("获取日出日落失败, 将计算昼夜")
            picture_name = judging_day_and_night(latitude, longitude)
        config["icon"] = (
            f"https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow_{picture_name}.png"
        )
