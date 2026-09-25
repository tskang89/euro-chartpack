# -*- coding: utf-8 -*-
"""계열 하나하나가 어느 데이터셋의 어느 칸인지.

이 파일이 차트팩의 사실상 명세다. 화면에 보이는 숫자를 고치려면 여기부터 본다.

유로지역은 EA21 로 잡는다. EA 는 그때그때 회원국이 바뀌는 집계라 과거와 현재가
같은 기준이 아니다. 2026-07 물가가 EA 2.9 / EA21 3.0 으로 갈리는 것이 그 예다.
차트팩은 불가리아 가입 이후 기준(EA21, 과거 소급)으로 통일한다.
"""

from __future__ import annotations

# 화면의 탭 순서. 키는 데이터 블록 이름, 값은 Eurostat geo 코드.
GEO = {
    "EZ": "EA21", "DE": "DE", "FR": "FR", "IT": "IT",
    "ES": "ES", "NL": "NL", "BE": "BE", "IE": "IE", "AT": "AT",
}
CODES = list(GEO.values())

# ---------------------------------------------------------------- 월간 (60개월)
MONTHLY = {
    "cpiM":  ("prc_hicp_minr", dict(coicop18="TOTAL", unit="RCH_A")),
    "coreM": ("prc_hicp_minr", dict(coicop18="TOT_X_NRG_FOOD", unit="RCH_A")),

    # 실업률은 계절조정(SA). 원계열은 달마다 튀어 추세를 못 본다.
    "unM":   ("une_rt_m", dict(s_adj="SA", age="TOTAL",  unit="PC_ACT", sex="T")),
    "ynM":   ("une_rt_m", dict(s_adj="SA", age="Y_LT25", unit="PC_ACT", sex="T")),

    # 마스트리흐트 수렴기준 10년물. 월평균이다.
    "y10":   ("irt_lt_mcby_m", dict(int_rt="MCBY")),

    # 생산지수는 2021=100. 계절·영업일수 조정(SCA).
    "ipT":   ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="B-D",     s_adj="SCA", unit="I21")),
    "ipM":   ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="C",       s_adj="SCA", unit="I21")),
    "ipS":   ("sts_sepr_m", dict(indic_bt="PRD", nace_r2="H-N_X_K", s_adj="SCA", unit="I21")),

    # 소매판매는 자동차를 뺀 소매업(G47) 판매 '물량'. 연료(G473)는 들어 있다.
    # 화면 각주가 "자동차·연료 제외"라고 적고 있으나 실제 계열은 G47 이다.
    # 연료까지 뺀 G47_X_G473 으로 받으면 저장값과 전부 어긋난다(101.9 대 102.2).
    "rt":    ("sts_trtu_m", dict(indic_bt="VOL_SLS", nace_r2="G47",
                                 s_adj="SCA", unit="I21")),

    # EC 기업·소비자 서베이
    "esi":   ("ei_bssi_m_r2", dict(indic="BS-ESI-I",     s_adj="SA")),
    "ici":   ("ei_bssi_m_r2", dict(indic="BS-ICI-BAL",   s_adj="SA")),
    "sci":   ("ei_bssi_m_r2", dict(indic="BS-SCI-BAL",   s_adj="SA")),
    "cc":    ("ei_bssi_m_r2", dict(indic="BS-CSMCI-BAL", s_adj="SA")),
}

# ---------------------------------------------------------------- 분기 (20분기)
QUARTERLY = {
    "gqq": ("namq_10_gdp", dict(s_adj="SCA", unit="CLV_PCH_PRE", na_item="B1GQ")),
    "gqy": ("namq_10_gdp", dict(s_adj="SCA", unit="CLV_PCH_SM",  na_item="B1GQ")),
}

# 경상수지는 상대가 나라마다 다르다. 유로지역은 역외(EXT_EA21) 거래가 기준이고,
# 개별 나라는 대세계(WRL_REST)다. 유로지역에 대세계를 쓰면 회원국끼리의 거래가
# 양쪽으로 잡혀 의미가 흐려진다.
CA_PARTNER = {"EA21": "EXT_EA21"}
CA_DEFAULT = "WRL_REST"

# ---------------------------------------------------------------- 연간 (5개년)
ANNUAL = {
    "gdpEur": ("nama_10_gdp", dict(unit="CP_MEUR",     na_item="B1GQ")),
    "ga":     ("nama_10_gdp", dict(unit="CLV_PCH_PRE", na_item="B1GQ")),
    # 국민계정 인구는 천 명 단위로 온다. 화면은 백만 명이라 1000 으로 나눈다.
    "pop":    ("nama_10_pe",  dict(unit="THS_PER", na_item="POP_NC"), 1 / 1000),

    "cpiA":   ("prc_hicp_ainr", dict(coicop18="TOTAL",          unit="RCH_A_AVG")),
    "coreA":  ("prc_hicp_ainr", dict(coicop18="TOT_X_NRG_FOOD", unit="RCH_A_AVG")),

    "unA":    ("une_rt_a", dict(age="Y15-74", unit="PC_ACT", sex="T")),
    "ynA":    ("une_rt_a", dict(age="Y15-24", unit="PC_ACT", sex="T")),

    # EDP 기준 일반정부. GD=총부채, B9=순대출(+)/순차입(−).
    "debt":   ("gov_10dd_edpt1", dict(unit="PC_GDP", sector="S13", na_item="GD")),
    "bal":    ("gov_10dd_edpt1", dict(unit="PC_GDP", sector="S13", na_item="B9")),

    "hpi":    ("prc_hpi_a", dict(purchase="TOTAL", unit="RCH_A_AVG")),
}

# ---------------------------------------------------------------- 아직 옮기지 않은 것
# 이유가 제각각이라 한 번에 묶을 수 없다. 옮기기 전까지는 이전 판의 값을 그대로
# 물려 쓴다(build.py 의 carry). 물려 쓴 계열은 빌드 로그에 남는다.
#
#   trA trQ      교역. 데이터셋이 유로지역(ext_st_easitc)과 개별국(ei_eteu27_2020_m)
#                으로 갈리고, 역내·역외 구분이 나라마다 다르다.
#   kr           대한국 교역. Comext(DS-045409)는 배포 API 와 다른 경로다.
#   imm immR     이민. 연간이고 발표가 늦다. 미발표국이 있으면 합계를 내지 않는다.
#   itH itC      HICP 세부 항목. 어느 코드 몇 개를 쓰는지 화면 코드에서 되짚어야 한다.
#   stk stkR     주가지수. Yahoo Finance 는 공식 API 가 아니라 언제든 막힐 수 있다.
#                무인 작업에 그대로 매달면 안 된다.
#   caQ caQp     경상수지. 상대·조정 기준을 저장값과 맞춰 봐야 한다.
#   caA caAp     연간 경상수지.
CARRY_OVER = ["trA", "trQ", "kr", "imm", "immR", "itH", "itC",
              "stk", "stkR", "caQ", "caQp", "caA", "caAp"]


# ------------------------------------------------- 계열마다 다른 처리
# 유로지역 값을 EA21 이 아닌 곳에서 받아야 하는 계열.
# 10년물 수렴기준 금리는 EA21 집계가 없다. Eurostat 이 EA 로만 낸다.
GEO_OVERRIDE = {
    "y10": {"EZ": "EA"},
}

# 저장할 자릿수. 화면이 보여 주는 만큼만 남긴다. 그래야 판마다 꼬리 숫자가
# 달라져 쓸데없는 변경이 생기지 않는다. 적지 않은 계열은 소수점 한 자리.
ROUND = {"gdpEur": 0, "pop": 2, "y10": 2, "spr": 0}
ROUND_DEFAULT = 1
