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

    # 소매판매 항목별. 사무소 월중동향이 '연료는 올랐으나 식료품이 내렸다'
    # 식으로 쓰는 둘이다. 비식료품은 Eurostat 코드가 따로 없다.
    "rtF":   ("sts_trtu_m", dict(indic_bt="VOL_SLS", nace_r2="G47_FOOD",
                                 s_adj="SCA", unit="I21")),
    "rtE":   ("sts_trtu_m", dict(indic_bt="VOL_SLS", nace_r2="G473",
                                 s_adj="SCA", unit="I21")),

    # 산업생산 항목별(주요 산업군, MIG). 전체 지수가 멈춰 있어도 자본재가
    # 빠지고 비내구재가 받치는 식의 안쪽 움직임이 보인다. 월중동향이
    # 산업생산을 쓸 때 늘 이 넷으로 쪼갠다.
    "ipCap": ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="MIG_CAG",
                                 s_adj="SCA", unit="I21")),
    "ipInt": ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="MIG_ING",
                                 s_adj="SCA", unit="I21")),
    "ipDur": ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="MIG_DCOG",
                                 s_adj="SCA", unit="I21")),
    "ipNdr": ("sts_inpr_m", dict(indic_bt="PRD", nace_r2="MIG_NDCOG",
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

# ------------------------------------- 주변국 국채금리 (탭 없이 선만)
# 사무소 월중동향은 주변국 스프레드를 이탈리아·스페인·포르투갈·그리스 평균으로
# 쓰는데 차트팩에는 포르투갈·그리스가 없었다. 두 나라 탭을 새로 만들 것까지는
# 없고(나머지 지표를 다 받아야 한다) 스프레드 차트에 선만 더한다.
#
# Eurostat 은 그리스를 EL 로 쓴다. GR 로 부르면 조용히 빈 값이 온다.
PERIPHERY = {"sprPT": "PT", "sprEL": "EL"}

# ------------------------------------- HICP 품목별 기여도 (자체 계산)
# 보고서가 쓰는 '소비자물가 상승에 대한 품목별 기여도(%p)' 다.
#
# Eurostat 공식 계열(prc_hicp_ctrb)은 2025-12 에서 멈춰 있다. 그래서 직접
# 낸다 — 기여도 = 그 품목의 전년동월비 × 가중치/1000.
#
# 공식 산식은 전년 지수비까지 쓰므로 소수 둘째 자리에서 조금 다를 수 있다.
# 차트 각주에 '자체 계산'이라고 밝힌다. 공식치와 같은 이름을 달면 안 된다.
#
# 가중치는 해마다 바뀐다. 그 달이 속한 해의 가중치를 쓰되, 아직 공표되지
# 않은 해(연초에는 흔하다)는 가장 최근 해의 것으로 잇는다.
#
# 넷을 더하면 전체 상승률이 된다. 2025년 가중치 합이 999.99 로 전체를 덮는다.
HICP_CTRB = {"ctrFood": "FOOD", "ctrGoods": "IGD_NNRG",
             "ctrNrg": "NRG", "ctrServ": "SERV"}

# 가중치(prc_hicp_inw)는 유로지역을 EA21 로 내지 않는다. 상승률 쪽은 EA21 이
# 되므로 둘이 어긋난다 — 처음에 유로지역 기여도만 통째로 비었다. 대체 코드를
# 순서대로 시도한다.
HICP_W_ALT = ["EA20", "EA19", "EA"]

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

# 한국 헤드라인·근원 물가도 ECOS 에서 직접 받는다(2026-10-05).
#
# 전에는 OECD 를 거쳤다. 그런데 OECD 는 각국 발표를 몇 주 뒤에 모아 싣는다 —
# 한국이 9월 물가를 10월 2일에 냈는데도 차트팩에는 8월치가 걸려 있었다.
# 사무소에서 제일 먼저 보는 숫자가 사흘 넘게 묵은 채로 떠 있던 셈이다.
#
# 품목별 막대를 받느라 이 표를 이미 부르고 있어 비용도 늘지 않는다.
#
# 미국·중국·일본은 OECD 그대로 둔다. 그 셋은 9월치를 아직 **발표하지도**
# 않았으므로 OECD 가 늦어서 비는 것이 아니다. 그래서 화면에서 한국 줄만
# 한 달 앞서 가는데, 그것은 어긋난 것이 아니라 발표 시차 그대로다.
#
# DB(식료품 및 에너지 제외)를 근원으로 쓴다. OECD 가 주던 _TXCP01_NRG 와
# 같은 정의다 — 한국 전통 기준인 QB(농산물·석유류 제외)가 아니다.
KR_CPI_MAIN = {
    "cpiM":  ("0",  KR_CPI_TABLE),
    "coreM": ("DB", KR_CPI_SPECIAL),
}

# 한국 정책금리도 ECOS 에서 직접 받는다(2026-10-05). BIS 는 나라마다 싣는
# 속도가 달라 한국이 늘 뒤처진다 — 미국·일본·중국이 10월까지 와 있는데
# 한국만 8월에서 멈춰, 빈 달이 둘이 되자 bis.fill_tail 의 한 달 한도를 넘겨
# 9·10월이 통째로 비었다. 기준금리는 한국은행이 제 손으로 정하는 숫자이고
# ECOS 가 날마다 싣는다.
KR_POLICY_RATE = ("722Y001", "0101000")    # 1.3.1. 한국은행 기준금리

# 한국 산업생산의 **꼬리만** ECOS 로 이어 붙인다(2026-10-05). 한국이 8월분을
# 9월 30일에 냈는데 OECD 에는 7월까지만 와 있었다.
#
# 통째로 갈지 않고 꼬리만 잇는 까닭. OECD 는 '건설 제외 산업'(BTE)이고 이
# 계열은 '광업 및 제조업'이라 **지수 기준과 범위가 다르다.** 수준을 바꿔
# 끼우면 지난 몇 해 선이 통째로 움직인다. 전월대비 증감률만 빌려 와 OECD
# 가 멈춘 지점부터 이어 붙이면 기준은 그대로 두고 최근 한두 달만 메운다.
# 두 계열의 전월대비는 광공업이 산업 전체를 거의 다 차지해 거의 같다.
KR_IP = ("901Y032", "I11AA")               # 8.3.1. 산업별 생산지수 — 광업 및 제조업


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
# 엔/유로를 더한다. 월중동향이 달러/유로와 나란히 놓고 보는 짝이다.
FX_MONTHLY = {"fxUsd": ("USD", 4), "fxKrw": ("KRW", 2),
              "fxJpy": ("JPY", 2)}
FX_ANNUAL = {"fxA": "USD"}
POLICY = {"dfr": "D.U2.EUR.4F.KR.DFR.LEV", "mro": "D.U2.EUR.4F.KR.MRR_FR.LEV"}

# 반올림을 어느 값에서 하는가. 출처마다 다르다.
#   binary  — 부동소수점이 실제로 담은 값. Eurostat 계열이 그렇다(2.405 는 2.40).
#   decimal — 글자 그대로의 값. ECB 환율이 그렇다(1.05785 는 1.0579).
# 원본 차트팩이 그렇게 만들어져 있어 그대로 따른다. 섞으면 마지막 자리가 틀어진다.
ROUND_MODE = {"fxUsd": "decimal", "fxKrw": "decimal", "fxJpy": "decimal"}


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
    # ACTIVITY 를 반드시 박는다. KEI 는 이 조합에 BTE(건설 제외 산업)·
    # C(제조업)·F(건설) 셋을 함께 주는데, 안 박아 두면 마지막에 온 것이
    # 남는다. 그래서 중국·미국·한국 칸에 **건설업** 지수가 '산업생산'이라는
    # 이름을 달고 여러 달 나갔다(중국 46.3 은 산업생산이 반토막 난 것이
    # 아니라 2015년 대비 건설이 반토막 난 것이다). 일본만 제조업이었다.
    #
    # BTE 를 고른 까닭은 이 자리의 이름이 '산업생산'이기 때문이다. 제조업만
    # 보려면 C 를 쓰는 별도 계열을 두어야 한다.
    "ipM":   ("KEI", dict(MEASURE="PRVM",   UNIT_MEASURE="IX",
                          ACTIVITY="BTE"), 1),

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

# ------------------------------------------------------------------ 은행·신용
# 차트팩에 금융중개가 통째로 비어 있었다. 독자 넷 가운데 하나가 프랑크푸르트
# 소재 한국계 은행인데 그들 업무에 닿는 자리가 없었다.
#
# 금리(MIR)는 회원국별로 다 있다. 신규 취급분 기준이라 정책금리 변화가 몇
# 달 안에 들어오는 것이 보인다.
ECB_MIR = {
    "crNfc":   "M.{geo}.B.A2A.A.R.A.2240.EUR.N",    # 기업 신규대출
    "crHouse": "M.{geo}.B.A2C.AM.R.A.2250.EUR.N",   # 가계 주택대출
    "dpTime":  "M.{geo}.B.L22.F.R.A.2250.EUR.N",    # 가계 예금(약정만기)
    "dpOvern": "M.{geo}.B.L21.A.R.A.2250.EUR.N",    # 가계 예금(수시입출)
}

# 대출 증가율(BSI)은 유로지역만 공표된다. 회원국은 잔액만 있고, 잔액에서
# 전년동월비를 직접 내면 ECB 공식 증가율과 다르다 — 재분류·유동화·환율
# 효과를 걷어낸 '거래 기준' 증가율이기 때문이다. 직접 계산한 값을 공식치와
# 같은 이름으로 싣지 않는다. 그래서 이 둘은 유로지역 탭에만 둔다.
ECB_BSI_EA = {
    "lnNfc":   "M.U2.Y.U.A20T.A.I.U2.2240.Z01.A",   # 기업 대출
    "lnHouse": "M.U2.Y.U.A20T.A.I.U2.2250.Z01.A",   # 가계 대출
}

# 은행대출서베이(BLS). 분기, 유로지역만. 순비율(%p) — 조였다는 응답 비율에서
# 풀었다는 응답 비율을 뺀 값이라 0 위면 조이는 쪽이 많다는 뜻이다.
#
# 키를 찾는 데 애를 먹었다. 차원이 열 개이고 항목 코드가 140개인데 이름으로는
# 'credit standard' 가 엉뚱한 것 하나에만 걸린다. 결국 실존 계열 22,843개를
# 전부 펼쳐 조합을 눈으로 확인했다. 요령은 둘이다.
#   · BLS_ITEM 'O'(Overall)가 헤드라인이고 나머지 139개는 기여 요인이다.
#   · 신용기준은 EFFECT_DOMAIN 'ST', 대출수요는 'ZZ'+MARKET_ROLE 'D',
#     여신조건은 'TC' 다.
#
# 가계는 '신용기준'이 Overall 로 공표되지 않는다. 여신조건(TC)만 있다.
# 없는 것을 있는 것처럼 적을 수 없으므로 그대로 둔다.
# ------------------------------------------------------------------ 값 점검
# 있을 수 없는 값을 못 박아 둔다.
#
# 비거나 터지는 고장은 바로 안다. 무서운 것은 엉뚱한 계열이 들어앉는 쪽이다 —
# 숫자가 그럴듯해서 눈에 띄지 않는다. 2026-10-01 에 소장이 "중국 산업생산이
# 너무 낮은 거 아니야?" 하고 묻기까지, 건설업 지수가 '산업생산'이라는 이름으로
# 여러 달 나갔다. 사람 눈이 유일한 그물이었다.
#
# (아래, 위). 벗어나면 빌드 경고 -> ops -> 주간 점검으로 나간다. 값을 고치지는
# 않는다 — 무엇이 맞는지는 사람이 봐야 한다.
#
# 범위는 넉넉하게 잡는다. 좁게 잡으면 멀쩡한 날에도 울리고, 매주 울리는 경고는
# 곧 무시된다. 잡으려는 것은 '조금 이상한 값'이 아니라 단위·부호·계열이
# 통째로 틀어진 경우다.
BOUNDS = {
    "unM": (0, 30), "unA": (0, 30), "ynM": (0, 70), "ynA": (0, 70),
    "cpiM": (-5, 40), "cpiA": (-5, 40), "coreM": (-5, 40), "coreA": (-5, 40),
    "y10": (-2, 25), "cbr": (-2, 25), "spr": (-300, 3000),
    "gqq": (-25, 25), "gqy": (-25, 30), "ga": (-25, 30),
    "debt": (0, 300),
    # 하한이 0 이 아니다. 2021~22년에 독일·네덜란드·벨기에의 수시입출
    # 예금금리가 실제로 마이너스였다(-0.01~-0.07%). 처음에 0 으로 잡았다가
    # 멀쩡한 값 넷이 걸려 고쳤다 — 범위는 넉넉해야 한다.
    "crNfc": (-1, 25), "crHouse": (-1, 25),
    "dpTime": (-1, 25), "dpOvern": (-1, 25),
    "lnNfc": (-25, 50), "lnHouse": (-25, 50),
    "blsNfcStd": (-100, 100), "blsNfcDem": (-100, 100),
    "blsNfcTc": (-100, 100), "blsHouseTc": (-100, 100),
    "blsConsTc": (-100, 100),
    "hpi": (-40, 60), "stkR": (-50, 50),
}

# 또래끼리 견주는 점검.
#
# 범위만으로는 중국 산업생산을 못 잡는다 — 46 은 지수로서 있을 수 있는 값이다.
# 잡아낸 것은 '다른 나라는 92~196 인데 혼자 46' 이라는 사실이었고, 그것이 바로
# 소장이 본 것이다. 그 눈을 기계에 옮긴다.
#
# 같은 기준연도를 쓰는 묶음 안에서만 견준다. 유로지역은 Eurostat 2021=100,
# 해외는 OECD 2015=100 이라 서로 견주면 안 된다.
#
# 지수에만 쓴다. 금리·실업률에 배수 비교를 걸면 일본 10년물(1.5%)이 미국
# (5.2%) 대비 0.29배라고 매번 울린다 — 그건 고장이 아니라 사실이다.
PEER_RATIO = {"ipM", "cli"}
PEER_GROUPS = [("EZ", "DE", "FR", "IT", "ES", "NL", "BE", "IE", "AT"),
               ("US", "CN", "JP", "KR")]
PEER_LOW, PEER_HIGH = 0.5, 2.0      # 중앙값의 몇 배를 벗어나면 짚을 것인가


ECB_BLS_EA = {
    "blsNfcStd":  "Q.U2.ALL.O.E.Z.B3.ST.S.WFNET",   # 기업 신용기준
    "blsNfcDem":  "Q.U2.ALL.O.E.Z.B3.ZZ.D.WFNET",   # 기업 대출수요
    "blsNfcTc":   "Q.U2.ALL.O.E.Z.B3.TC.S.WFNET",   # 기업 여신조건
    "blsHouseTc": "Q.U2.ALL.O.H.H.B3.TC.S.WFNET",   # 가계 주택 여신조건
    "blsConsTc":  "Q.U2.ALL.O.H.C.B3.TC.S.WFNET",   # 소비자신용 여신조건
}

# 회원국 코드. ECB 는 유로지역을 U2 로 쓴다(Eurostat 의 EA21 이 아니다).
ECB_GEO = {"EZ": "U2", "DE": "DE", "FR": "FR", "IT": "IT", "ES": "ES",
           "NL": "NL", "BE": "BE", "IE": "IE", "AT": "AT"}

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
# 마지막 칸이 ADJUSTMENT 다. 비워 두면 계절조정판(Y)과 원계열(N)이 함께 와서
# 받는 쪽에서 마지막 것만 남는다. 분기마다 어느 쪽이 남는지가 응답 순서에
# 달려 있어, 한 선 안에서 두 계열이 섞였다 — 한국 2024-Q4 가 32,059 와
# 27,592 사이에서, 중국 2023-Q4 는 40,657 과 57,732 사이에서 갈렸다(42% 차).
#
# N(원계열)으로 박는다. 유로지역 쪽이 Eurostat 에서 s_adj="NSA" 로 받고 있어
# 그것과 같은 눈금이어야 탭을 넘나들며 견줄 수 있다.
OECD_CA_KEY = "USA+CHN+JPN+KOR.WXD.CA.B..{freq}.USD_EXC.N"

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

# 미국·중국·일본의 대한국 교역.
#
# 유로지역은 Eurostat 에 상대국 한국이 들어 있어 유럽 측 통계를 그대로 쓴다.
# 이 셋은 한 군데서 받을 곳이 없다 — 미국 센서스·중국 해관총서·일본 재무성을
# 각각 붙여야 하고, 한 데 모은 IMF DOTS 는 분기 이상으로 늦다.
#
# 그래서 한국은행 ECOS 의 국가별 수출입(관세청 통관 기준)을 거울상으로 쓴다.
# 한국의 대미 수출이 곧 미국의 대한국 수입이다. 그래서 ex/im 이 뒤집힌다.
#
# 901Y121 국가별 수출입. T002 수출금액, T004 수입금액. 단위는 천달러.
#
# 유로지역 차트와 집계 기준이 다르다는 것을 각주에 밝힌다. 유럽 쪽은 유럽이
# 신고한 값이고 이쪽은 한국이 신고한 값이라, 같은 교역도 금액이 어긋난다
# (수출은 FOB, 수입은 CIF 로 잡혀 운임·보험이 한쪽에만 붙는다).
KR_TRADE_TABLE = "901Y121"
KR_TRADE_FLOW = {"ex": "T004", "im": "T002"}
KR_TRADE_AREAS = {"US": "US", "CN": "CN", "JP": "JP"}
