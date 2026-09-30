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
    # 원본 각주가 "자동차·연료 제외"라고 적고 있었으나 사실과 달라 2026-09-25 에
    # 고쳤다. 연료까지 뺀 G47_X_G473 으로 받으면 값이 전부 어긋난다(101.9 대 102.2).
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
CARRY_OVER = []


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


# ------------------------------------------------- 품목별 소비자물가 (가로 막대)
# 화면의 항목 순서와 정확히 같아야 한다. 이름표는 template.html 에 박혀 있고
# 여기서는 값만 그 순서로 채운다. 순서가 어긋나면 엉뚱한 막대에 숫자가 붙는데,
# 차트는 멀쩡해 보이므로 눈으로는 못 잡는다.
ITEM_MONTH_KEY = "hicpItemMonth"        # meta 의 어느 달을 쓰는지

ITEMS = {
    # 전체 / 식료품·주류·담배(가공·미가공) / 에너지(전기가스·연료) / 공업제품 / 서비스
    "itH": ["TOTAL", "FOOD", "FOOD_P", "FOOD_NP",
            "NRG", "ELC_GAS", "FUEL", "IGD_NNRG", "SERV"],
    # 근원 / 비에너지 공업제품(내구·준내구·비내구) / 서비스(주거·교통·통신·여가·기타)
    "itC": ["TOT_X_NRG_FOOD", "IGD_NNRG", "IGD_NNRG_D", "IGD_NNRG_SD",
            "IGD_NNRG_ND", "SERV", "SERV_HOUS", "SERV_TRA", "SERV_COM",
            "SERV_REC", "SERV_MSC"],
}

# ------------------------------------- 독일 ifo · 프랑스 INSEE 업황지수
# EC 서베이(ei_bssi_m_r2)는 유럽 전체를 같은 잣대로 묶은 것이라 나라 사이를
# 견주기에 좋다. 그런데 독일·프랑스 현지에서 실제로 인용되는 것은 각국
# 자체 조사다 — 독일은 ifo, 프랑스는 INSEE. 둘을 함께 둔다.
#
# 단위가 다르다는 점이 중요하다.
#   ifo 전체      지수, 2015 = 100
#   ifo 부문별    잔액(좋다 − 나쁘다, %p)  ← 지수가 아니다
#   INSEE 셋 다   지수, 장기평균 = 100
# 그래서 ifo 는 화면에서 전체와 부문별을 따로 그린다.
SURVEY_DE = {"ifoA": "all", "ifoM": "man", "ifoS": "srv"}
SURVEY_FR = {"insA": "001565530",     # 전체(tous secteurs)
             "insM": "001585934",     # 제조업(industrie manufacturière)
             "insS": "001587025"}     # 서비스(services)


# ------------------------------------- 한국 품목별 소비자물가 (ECOS)
# 유로지역 탭에는 품목별 막대가 있는데 한국 탭에는 없었다. OECD 는 한국의
# 헤드라인·근원만 주고 품목 구성을 주지 않아, 한국은행 ECOS 에서 직접 받는다.
#
# ECOS 는 지수를 주므로 상승률은 전년동월과 견줘 코드에서 낸다.
#
# 화면의 이름표 순서와 정확히 같아야 한다. 유로 쪽과 같은 함정이다 —
# 순서가 어긋나도 차트는 멀쩡해 보인다.
KR_CPI_TABLE = "901Y009"          # 4.2.1. 소비자물가지수 (COICOP 대분류)
KR_CPI_SPECIAL = "901Y010"        # 4.2.2. 소비자물가지수(특수분류)

KR_ITEMS = {
    # 총지수 + COICOP 12 대분류
    "itH": [("0", KR_CPI_TABLE), ("A", KR_CPI_TABLE), ("B", KR_CPI_TABLE),
            ("C", KR_CPI_TABLE), ("D", KR_CPI_TABLE), ("E", KR_CPI_TABLE),
            ("F", KR_CPI_TABLE), ("G", KR_CPI_TABLE), ("H", KR_CPI_TABLE),
            ("I", KR_CPI_TABLE), ("J", KR_CPI_TABLE), ("K", KR_CPI_TABLE),
            ("L", KR_CPI_TABLE)],
    # 근원을 **이루는** 항목만 담는다.
    #
    # 처음에는 상품·서비스 전체 갈래를 넣었다가 근원 차트에 석유류(+14%)와
    # 농축수산물이 나란히 서는 그림이 됐다. 근원은 바로 그 둘을 빼고 재는
    # 것인데, 제목 밑에 그것들이 있으면 근원에 든 것으로 읽힌다.
    #
    # 한국은 근원을 둘로 낸다 — 국제 기준(DB: 식료품·에너지 제외)과 한국
    # 전통 기준(QB: 농산물·석유류 제외). 둘을 맨 위에 기준선으로 둔다.
    # 나머지는 DB 근원에 들어가는 서비스와 공업제품이다. 공업제품 상위
    # 항목(212)은 가공식품·석유류를 품고 있어 넣지 않고 세부만 싣는다.
    "itC": [("DB", KR_CPI_SPECIAL), ("QB", KR_CPI_SPECIAL),
            ("22", KR_CPI_SPECIAL), ("221", KR_CPI_SPECIAL),
            ("222", KR_CPI_SPECIAL), ("223", KR_CPI_SPECIAL),
            ("2231", KR_CPI_SPECIAL), ("2239", KR_CPI_SPECIAL),
            ("2122", KR_CPI_SPECIAL), ("2123", KR_CPI_SPECIAL),
            ("2127", KR_CPI_SPECIAL), ("2129", KR_CPI_SPECIAL)],
    # 근원에서 **빠지는** 변동성 항목. 한국 물가 논의는 늘 이쪽이 중심이라
    # 버리지 않고 따로 싣는다. 근원과 섞지만 않으면 된다.
    "itX": [("10", KR_CPI_SPECIAL), ("211", KR_CPI_SPECIAL),
            ("2111", KR_CPI_SPECIAL), ("2112", KR_CPI_SPECIAL),
            ("2113", KR_CPI_SPECIAL), ("2121", KR_CPI_SPECIAL),
            ("2125", KR_CPI_SPECIAL), ("213", KR_CPI_SPECIAL),
            ("110", KR_CPI_SPECIAL)],
}
KR_ITEM_BLOCK = "KR"


# ------------------------------------------------------------------ 경상수지
# 상대가 나라마다 다르다. 유로지역은 역외(EXT_EA21) 거래가 기준이고 개별 나라는
# 대세계(WRL_REST)다. 유로지역에 대세계를 쓰면 회원국끼리의 거래가 양쪽으로
# 잡혀 뜻이 흐려진다.
#
# 금액(caQ·caA)은 달러 환산이다. 유로 금액을 그 분기의 평균 EUR/USD 로 곱하고,
# 연간은 분기 환산액을 더한다. 연 평균 환율로 한 번에 곱하면 분기별 환율 차이가
# 뭉개져 값이 달라진다.
# GDP 대비 비율의 연간치(caAp)는 연간 경상수지(유로) ÷ 연간 명목 GDP 로 낸다.
# 원본 각주는 "Eurostat 공표치"라고 적었는데, Eurostat 의 연간 국제수지는 분기
# 합계와 꼭 같지 않다(연간 편제가 따로 있다). 그래서 45개 값 중 5개가 0.1~0.4%p
# 어긋난다 — DE 2024, NL 2024, IE 2022·2023·2025. 공표 연간 계열(bop_c6_a)은
# 차원 이름이 분기 계열과 달라 그대로 갖다 쓸 수 없었다.
# 지금 방식은 분기 자료와 앞뒤가 맞는다는 장점이 있다. 공표치로 바꾸려면
# bop_c6_a 의 차원을 먼저 확인할 것.
CA_FILTERS = dict(bop_item="CA", stk_flow="BAL", s_adj="NSA",
                  sector10="S1", sectpart="S1")
CA_PARTNER = {"EA21": "EXT_EA21"}
CA_DEFAULT = "WRL_REST"

# ------------------------------------------------------------------ ECB
FX_MONTHLY = {"fxUsd": ("USD", 4), "fxKrw": ("KRW", 2)}
FX_ANNUAL = {"fxA": "USD"}
POLICY = {"dfr": "D.U2.EUR.4F.KR.DFR.LEV", "mro": "D.U2.EUR.4F.KR.MRR_FR.LEV"}

# 반올림을 어느 값에서 하는가. 출처마다 다르다.
#   binary  — 부동소수점이 실제로 담은 값. Eurostat 계열이 그렇다(2.405 는 2.40).
#   decimal — 글자 그대로의 값. ECB 환율이 그렇다(1.05785 는 1.0579).
# 원본 차트팩이 그렇게 만들어져 있어 그대로 따른다. 섞으면 마지막 자리가 틀어진다.
ROUND_MODE = {"fxUsd": "decimal", "fxKrw": "decimal"}


# ------------------------------------------------------------------ 이민
# 연간이고 발표가 한참 늦다(지금은 2024년이 마지막). 기간 축도 다르다 —
# meta.yearsM 를 쓴다.
#
# Eurostat 이민 통계는 유로지역 집계를 따로 내지 않는다. 21개 회원국을 더한다.
# 한 나라라도 빠진 해는 합계를 내지 않고 비운다 — 스무 나라 합을 스물한 나라
# 합인 양 보여 주면 그 해만 낮게 나오고, 그래프에서는 감소로 읽힌다.
# 빠진 나라는 meta.immMissing 으로 화면 각주에 이름이 나간다.
IMM_FILTERS = dict(citizen="TOTAL", agedef="REACH", age="TOTAL",
                   unit="NR", sex="T")

# 유로지역 21개 회원국.
#
# 그리스는 'EL' 이다. 'GR' 이 아니다. Eurostat 은 ISO 코드가 아니라 EU 관례를
# 쓴다. GR 로 물으면 오류가 나지 않고 빈 응답이 온다 — 그래서 "그리스는 이민
# 통계를 제출하지 않는다"고 잘못 읽기 쉽다. 실제로 한 번 그렇게 읽었다.
# 2020년 기준 그리스 몫은 84,221명으로, 그것이 빠지면 합계가 2,645천 명 대신
# 2,561천 명이 된다.
EA_MEMBERS = ["AT", "BE", "BG", "HR", "CY", "EE", "FI", "FR", "DE", "EL",
              "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PT", "SK", "SI", "ES"]


# ------------------------------------------------------------------ 교역
# 유로지역과 개별국이 다른 데이터셋을 쓴다. '전체'의 뜻도 다르다.
#
#   유로지역  ext_st_easitc. 전체 = 역내(EA21) + 역외(EXT_EA21).
#             회원국끼리의 거래도 유로지역의 교역으로 친다.
#   개별국    ei_eteu27_2020_m. 전체 = 대세계(WORLD), 역외 = EU 27개국 밖.
#             기준이 유로지역이 아니라 EU 라는 점에 주의.
#
# 금액은 달러 환산이다. 월별 금액에 그달 평균 EUR/USD 를 곱하고 더한다.
# 연·분기 환율로 한 번에 곱하면 달마다 다른 환율이 뭉개져 값이 달라진다.
TRADE_EURO = ("ext_st_easitc", dict(indic_et="TRD_VAL", sitc06="TOTAL"),
              {"intra": "EA21", "extra": "EXT_EA21"})
TRADE_COUNTRY = ("ei_eteu27_2020_m", dict(unit="MIO-EUR-NSA", indic="ET-T"),
                 {"total": "WORLD", "extra": "EXT_EU27_2020"})

# 대한국 교역. 유로지역은 위 데이터셋에 상대국 KR 이 있지만, 개별국은 상대가
# 집계뿐이라 Comext 를 따로 불러야 한다(comext.py 참고).
KR = "KR"


# ============================================== 유로지역 밖 (미국·중국·일본·한국)
# Eurostat 은 EU 밖을 내지 않는다. 이 넷은 OECD SDMX 에서 받는다.
#
# 이름이 같은 계열이라도 정의가 유로지역과 똑같지는 않다. 유로지역 물가는
# HICP 이고 이쪽은 각국 CPI 다. 생산지수도 기준연도가 다를 수 있다. 차트가
# 나라별로 따로 그려지므로 한 그림에 섞이지는 않지만, 각주에 무엇인지 밝혀야
# 한다.
#
# 빈 곳이 셋 있다. 없는 것은 빈칸으로 둔다 — 0 으로 채우면 급락으로 읽힌다.
#
#   일본 소비자물가   KEI 에 없다. 전용 물가 데이터플로(DSD_PRICES@DF_PRICES_ALL)
#                     에도 JPN 은 안 나온다. 미국·한국·중국은 두 경로 값이 같으니
#                     코드를 잘못 짚은 것은 아니다. 다른 출처를 붙여야 한다.
#   중국 실업률       OECD 에 비교 가능한 계열이 없다. 중국은 도시조사실업률을
#                     내지만 기준이 다르다.
#   일본 기업심리     BCICP 에 JPN 이 없다. 일본은 단칸(日銀短観)이 따로 있다.
OECD_AREAS = {"US": "USA", "CN": "CHN", "JP": "JPN", "KR": "KOR"}

# (흐름, 차원 조건, 자릿수). 흐름은 oecd.py 의 KEI / FINMARK.
OECD_MONTHLY = {
    # 유로지역 차트와 같은 자리에 들어가는 것
    "cpiM":  ("KEI", dict(MEASURE="CP",     UNIT_MEASURE="GR",
                          TRANSFORMATION="GY"), 1),
    "y10":   ("KEI", dict(MEASURE="IRLT",   UNIT_MEASURE="PA"), 2),
    "unM":   ("KEI", dict(MEASURE="UNEMP",  UNIT_MEASURE="PT_LF"), 1),
    "ipM":   ("KEI", dict(MEASURE="PRVM",   UNIT_MEASURE="IX"), 1),

    # 새로 만드는 자리. 유로지역에는 대응 계열이 없거나 출처가 다르다.
    "bci":   ("KEI", dict(MEASURE="BCICP",  UNIT_MEASURE="PB"), 1),
    # 기업·소비자 심리는 각국 서베이의 '원래 눈금'으로 온다(UNIT=PB).
    # 미국 소비자는 50~85, 중국은 85~120, 한국은 -14~12 처럼 나라마다 척도가
    # 다르다. KEI 에 100 기준 진폭조정판(IX)은 없다. 그래서 이 계열로는
    # 나라 사이 수준을 견줄 수 없고, 각 나라의 방향과 추세만 읽어야 한다.
    # 처음에 각주를 "100 = 장기평균"이라고 적었다가 바로잡았다.
    "cci":   ("KEI", dict(MEASURE="CCICP",  UNIT_MEASURE="PB"), 1),

    # 경기선행지수(CLI). 이쪽은 100 이 장기추세라 나라 사이 비교가 된다.
    "cli":   ("KEI", dict(MEASURE="LI",     UNIT_MEASURE="IX"), 1),
    # 교역액은 월 10억 달러 단위로 온다(2026-08 중국 396, 미국 200, 한국 100).
    "exUSD": ("KEI", dict(MEASURE="EX",     UNIT_MEASURE="USD"), 1),
    "imUSD": ("KEI", dict(MEASURE="IM",     UNIT_MEASURE="USD"), 1),
}

# 한 나라만 다른 데이터플로에서 받아야 하는 계열.
#
# 일본 물가가 그렇다. KEI 에도, COICOP 1999 판 물가 데이터플로에도 JPN 이
# 없는데 COICOP 2018 판에는 있다. 미국·한국·중국은 거꾸로 1999 판에만 있다.
# OECD 가 분류 개편을 나라마다 다른 속도로 하고 있어 생긴 일이다. 한쪽만 보고
# "일본은 자료가 없다"고 읽기 쉽다 — 실제로 한 번 그렇게 읽었다.
#
# FRED 도 뒤져 봤지만 거기 일본 물가는 전부 OECD MEI 출처라 2021~22년에 함께
# 멈춰 있다. 살아 있는 것은 이 경로뿐이다.
#
# {계열: {블록: (흐름 전체 이름, 키, 자릿수)}}. 주 계열이 통째로 비었을 때만 쓴다.
OECD_FALLBACK = {
    "cpiM": {
        "JP": ("OECD.SDD.TPS,DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL,1.0",
               "JPN.M.N.CPI.PA._T.N.GY", 1),
    },
}

# 근원물가(식품·에너지 제외). 헤드라인과 마찬가지로 일본만 COICOP 2018 판이다.
#
# 유로 탭의 근원물가는 "에너지·식품·주류·담배 제외"(TOT_X_NRG_FOOD)라 정의가
# 조금 다르다. 술·담배가 들어 있고 빠져 있고의 차이다. 각주에 밝힌다.
#
# 중국은 없다. 전용 근원물가 데이터플로에도, 이 경로에도 CHN 이 안 나온다.
# 중국은 OECD 에 비교 가능한 근원 계열을 내지 않는다.
OECD_CORE = {
    "coreM": [("PRICES_99", "USA+KOR+CHN.M.N.CPI.PA._TXCP01_NRG.N.GY"),
              ("PRICES_18", "JPN.M.N.CPI.PA._TXCP01_NRG.N.GY")],
    "coreA": [("PRICES_99", "USA+KOR+CHN.A.N.CPI.PA._TXCP01_NRG.N.GY"),
              ("PRICES_18", "JPN.A.N.CPI.PA._TXCP01_NRG.N.GY")],
}

# 대유로 환율. ECB 기준환율에서 받는다(1유로당 자국통화).
# 미국은 달러지수를 쓰므로 여기 넣지 않는다 — 지수와 환율을 한 축에 겹치면
# 눈금이 뒤섞인다.
ECB_FX_PER_EUR = {"KR": "KRW", "JP": "JPY", "CN": "CNY"}

# 대미달러 환율. 미국은 자기 통화라 계열이 없다 — 빈칸으로 둔다.
OECD_FX = ("KEI", dict(MEASURE="CC", UNIT_MEASURE="XDC_USD"), 2)

# 분기 실질 GDP 성장률. 유로지역 차트와 같은 자리(gqq·gqy)에 들어간다.
#
# 이 흐름은 나라를 키로 좁히면 500 이 난다. "all" 로 받아 코드에서 거른다.
# 26개 지역이 와도 한 번 호출이라 오히려 빠르다.
# 연간 실업률. KEI 의 같은 계열을 연간 주기로 받는다. 중국은 월간과 마찬가지로
# 없다.
OECD_ANNUAL_UNEMP = dict(MEASURE="UNEMP", UNIT_MEASURE="PT_LF")

# 연간 계열. 기간 축은 meta.years.
#
# 실질 성장률은 G20 흐름의 연간 주기를 쓴다. OECD 회원국 전용 흐름
# (DF_TABLE1_EXPENDITURE_GROWTH)에는 중국이 없는데 G20 에는 있다.
OECD_ANNUAL_GROWTH = dict(TRANSACTION="B1GQ", TRANSFORMATION="G1",
                          UNIT_MEASURE="PC", SECTOR="S1", FREQ="A")

# 연간 물가도 월간과 같은 사정이다 — 일본만 COICOP 2018 판에 있다.
OECD_ANNUAL_CPI = {
    "USA+KOR+CHN": ("PRICES_99", "USA+KOR+CHN.A.N.CPI.PA._T.N.GY"),
    "JPN": ("PRICES_18", "JPN.A.N.CPI.PA._T.N.GY"),
}

# 총인구. 중국은 이 흐름에 없다(OECD 회원국 국민계정이라 그렇다).
OECD_POP_KEY = "A.USA+CHN+JPN+KOR.........."
OECD_POP_MATCH = dict(TRANSACTION="POP", UNIT_MEASURE="PS")

# 경상수지. 상대는 대세계(WXD), 항목은 경상수지(CA), 기표는 수지(B),
# 단위는 시장환율 달러(USD_EXC). 백만 달러로 와서 1000 으로 나눠 십억으로 쓴다.
#
# 분기 합이 연간과 맞는지 확인했다 — 한국 2025년 분기 26.7+28.8+31.1+36.5 =
# 123.1 로 연간 공표치와 정확히 같다. 미국·일본도 같았다.
OECD_CA_KEY = "USA+CHN+JPN+KOR.WXD.CA.B..{freq}.USD_EXC."

OECD_QUARTERLY = {
    "gqq": dict(TRANSACTION="B1GQ", TRANSFORMATION="G1", UNIT_MEASURE="PC",
                SECTOR="S1"),
    "gqy": dict(TRANSACTION="B1GQ", TRANSFORMATION="GY", UNIT_MEASURE="PC",
                SECTOR="S1"),
}

# 주가는 OECD 에도 있지만 지수(2021=100)다. 유로지역 차트는 실제 지수 수준을
# 보여 주므로 여기서도 Yahoo 월말 종가를 쓴다. 그래야 같은 차트가 된다.
OECD_STOCKS = {"US": "^GSPC", "CN": "000001.SS", "JP": "^N225", "KR": "^KS11"}

# 미국은 자기 통화라 대미달러 환율이 없다. 대신 달러지수(ICE DXY)를 넣는다.
# Yahoo 에서 받아 키가 필요 없다 — FRED 의 광의 달러지수를 쓰면 키에 매이게 된다.
# 단위가 다르다는 점은 화면 각주에서 밝힌다.
DOLLAR_INDEX = {"US": "DX-Y.NYB"}

# 진행 중인 달을 최근일로 채울 수 있는 국채금리. 미국뿐이다.
#
# Yahoo ^TNX(CBOE 10년 국채수익률 지수)의 월평균을 OECD 계열과 14개월 내내
# 견줬더니 1bp 안에서 같았다. 같은 계열로 봐도 된다.
#
# 유로지역은 넣지 못한다. Maastricht 수렴기준 금리는 정의가 월평균이라
# 일별 판이 아예 없고, 분데스방크의 일별 독일 금리(Svensson 곡선)는 8월
# 평균이 3.25 로 Eurostat 의 3.19 와 6bp 어긋나는 다른 계열이다.
DAILY_YIELD = {"US": "^TNX"}

# 한국 10년물은 야후에 티커가 없다. 한국은행 ECOS 의 시장금리(일별)에서 받는다.
# 817Y002 가 '시장금리(일별)', 010210000 이 국고채(10년)다.
#
# OECD 월간과 같은 계열이다 — 2026-05~08 의 일별 월평균이 4.08·4.18·4.29·4.29
# 로 차트팩에 실린 OECD 값과 소수 둘째 자리까지 맞았다. 독일처럼 계열이
# 어긋나는 문제가 없으므로 그대로 이어 붙인다.
#
# 키가 없는 데서는 이 줄만 조용히 빠진다.
ECOS_DAILY_YIELD = {"KR": ("817Y002", "010210000")}
