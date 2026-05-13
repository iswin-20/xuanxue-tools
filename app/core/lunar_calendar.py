#!/usr/bin/env python3
"""
Pure-Python Chinese Lunar Calendar converter.
Uses the standard compressed lookup table (years 1900-2100).
"""

from datetime import date, timedelta

# Heavenly Stems (天干)
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# Earthly Branches (地支)
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# Zodiac animals (生肖)
SHENG_XIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 12 Value Gods (值神 / 黄黑道)
VALUE_GODS = ["青龙", "明堂", "金匮", "天德", "玉堂", "司命", "天刑", "朱雀", "白虎", "天牢", "玄武", "勾陈"]

# 12 "建除" stars
JIAN_CHU = ["建", "除", "满", "平", "定", "执", "破", "危", "成", "收", "开", "闭"]

# Lunar month names
LUNAR_MONTHS = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]

# Lunar day names 1-10, 11-20, 21-30
LUNAR_DAY_1_10 = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十"]
LUNAR_DAY_11_20 = ["十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
LUNAR_DAY_21_30 = ["廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]

# Compressed lunar calendar data for 1900-2100
# Each entry: bits 0-3=leap month, 4-15=month lengths, 16-19=leap month length
LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x16a95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a4d0, 0x0d150, 0x0f252,
    0x0d520,
]

BASE_DATE = date(1900, 1, 31)  # 1900-01-01 lunar

# Value god mapping by earthly branch index
# 子→青龙(0), 丑→明堂(1), 寅→天刑(6), 卯→朱雀(7),
# 辰→金匮(2), 巳→天德(3), 午→白虎(8), 未→玉堂(4),
# 申→天牢(9), 酉→玄武(10), 戌→司命(5), 亥→勾陈(11)
GOD_BY_ZHI = [0, 1, 6, 7, 2, 3, 8, 4, 9, 10, 5, 11]


def _leap_month(year_idx):
    return LUNAR_INFO[year_idx] & 0xf


def _month_days(year_idx, month):
    """month 1-12 normal, 13 = leap month."""
    leap = _leap_month(year_idx)
    if month == 13:
        return 30 if (LUNAR_INFO[year_idx] & 0x10000) else 29
    return 30 if (LUNAR_INFO[year_idx] & (0x10000 >> month)) else 29


def _year_days(year_idx):
    total = sum(_month_days(year_idx, m) for m in range(1, 13))
    if _leap_month(year_idx):
        total += _month_days(year_idx, 13)
    return total


def solar_to_lunar(solar):
    delta = (solar - BASE_DATE).days
    if delta < 0:
        raise ValueError("Date before 1900-01-31")

    lunar_year = 1900
    year_idx = 0
    while year_idx < len(LUNAR_INFO):
        days = _year_days(year_idx)
        if delta < days:
            break
        delta -= days
        lunar_year += 1
        year_idx += 1

    if year_idx >= len(LUNAR_INFO):
        raise ValueError("Date after 2100")

    leap = _leap_month(year_idx)
    is_leap = False
    lunar_month = 1
    for m in range(1, 14):
        days = _month_days(year_idx, m)
        if delta < days:
            break
        delta -= days
        lunar_month += 1
    is_leap = (leap and lunar_month == leap + 1)

    lunar_day = delta + 1

    # Year ganzhi (1984=甲子年, cycle starts)
    year_offset = (lunar_year - 4) % 60
    year_gan_idx = year_offset % 10
    year_zhi_idx = year_offset % 12

    # Day ganzhi using 1900-01-01 = 甲戌日 as reference
    days_since_1900 = (solar - date(1900, 1, 1)).days
    day_gan_idx = days_since_1900 % 10
    day_zhi_idx = (days_since_1900 + 10) % 12

    # Month ganzhi
    month_gan_idx = (year_gan_idx * 2 + lunar_month) % 10
    month_zhi_idx = (lunar_month + 1) % 12

    # Value god
    value_god = VALUE_GODS[GOD_BY_ZHI[day_zhi_idx]]

    # Jianchu
    month_branch = (lunar_month + 1) % 12
    jian_idx = (day_zhi_idx - month_branch) % 12
    jianchu = JIAN_CHU[jian_idx]

    # Name formatting
    lunar_month_name = "闰" if is_leap else ""
    lunar_month_name += LUNAR_MONTHS[lunar_month - 1] + "月"

    if lunar_day <= 10:
        lunar_day_name = LUNAR_DAY_1_10[lunar_day - 1]
    elif lunar_day <= 20:
        lunar_day_name = LUNAR_DAY_11_20[lunar_day - 11]
    elif lunar_day <= 30:
        lunar_day_name = LUNAR_DAY_21_30[lunar_day - 21]
    else:
        lunar_day_name = str(lunar_day) + "日"

    return {
        "lunar_year": lunar_year,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "is_leap": is_leap,
        "lunar_month_name": lunar_month_name,
        "lunar_day_name": lunar_day_name,
        "year_gan": TIAN_GAN[year_gan_idx],
        "year_zhi": DI_ZHI[year_zhi_idx],
        "month_gan": TIAN_GAN[month_gan_idx],
        "month_zhi": DI_ZHI[month_zhi_idx],
        "day_gan": TIAN_GAN[day_gan_idx],
        "day_zhi": DI_ZHI[day_zhi_idx],
        "ganzhi_year": TIAN_GAN[year_gan_idx] + DI_ZHI[year_zhi_idx],
        "ganzhi_month": TIAN_GAN[month_gan_idx] + DI_ZHI[month_zhi_idx],
        "ganzhi_day": TIAN_GAN[day_gan_idx] + DI_ZHI[day_zhi_idx],
        "shengxiao": SHENG_XIAO[year_zhi_idx],
        "value_god": value_god,
        "jianchu": jianchu,
    }


def get_lunar_date(d=None):
    if d is None:
        d = date.today()
    return solar_to_lunar(d)


if __name__ == "__main__":
    today = date.today()
    info = get_lunar_date(today)
    print(f"公历: {today}")
    print(f"农历: {info['lunar_month_name']} {info['lunar_day_name']}")
    print(f"年干支: {info['ganzhi_year']} ({info['shengxiao']}年)")
    print(f"月干支: {info['ganzhi_month']}")
    print(f"日干支: {info['ganzhi_day']}")
    print(f"值神: {info['value_god']}")
    print(f"建除: {info['jianchu']}")
