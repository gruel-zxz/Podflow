SELECT DISTINCT 
  a.cust_id,
  a.biz_org,
  a.medium_id,
  a.last_fin_txn_dt,
  a.primacct_open_dt,
  a.PRIMACCT_AGMT_ID,
  q.LST_AGTPAY_DT,
  q.corp_name,
  z.AGTPAY_CORP_ID,
  z.AGTPAY_CORP_NAME,
  z.AGTPAY_CUST_ID,
  e.DPST_BAL_RMB, 
  e.statis_dt,
  e.ASSET_Y_AVG_BAL_RMB,
  e.FIN_Y_AVG_BAL_RMB,
  e.LOAN_BAL_RMB,
  e.LOAN_Y_AVG_BAL_RMB,
  f.tag_id,
  f.eff_dt,
  y.CURR_M_CUST_LEV_CD,
  z.TXN_DT,
  (CURRENT_DATE - q.LST_AGTPAY_DT) AS days_since_last_agreement
FROM BV_MTDVIEW.T03_NORM_MEDIUM AS a
LEFT JOIN bv_mtdview.C04_INDIV_CUST_ASSET_BAL AS e
  ON a.cust_id = e.cust_id AND e.statis_dt = CURRENT_DATE - INTERVAL '1 DAY'
LEFT JOIN bv_mtdview.T03_CUST_ACCT_LIM_VAL_TAG_INFO AS f
  ON a.PRIMACCT_AGMT_ID = f.agmt_id 
LEFT JOIN bv_mtdview.C01_B_INDIV_CUSTOMER AS j
  ON j.cust_id = a.cust_id AND j.statis_dt = CURRENT_DATE - INTERVAL '1 DAY'
LEFT JOIN bv_mtdview.C01_INDIV_CUST_ATTCH_INF AS q
  ON q.cust_id = a.cust_id AND q.statis_dt = CURRENT_DATE - INTERVAL '1 DAY'
LEFT JOIN (
  SELECT
    PAYEE_CUST_ID,
    AGTPAY_CORP_ID,
    AGTPAY_CORP_NAME,
    AGTPAY_CUST_ID,
    TXN_DT, 
    ROW_NUMBER() OVER (PARTITION BY PAYEE_CUST_ID ORDER BY txn_dt DESC) AS rn
  FROM BV_MTDVIEW.C05_S_AGTPAY_TXN_DTL
) AS z 
ON z.PAYEE_CUST_ID = a.cust_id AND z.rn = 1
LEFT JOIN BV_MTDVIEW.C06_INDIV_SYN_CUST_ALLOT_DTL AS y
  ON y.cust_id = a.cust_id
  AND y.PERF_DIM = '1'
  AND y.DATA_DT = CASE 
    WHEN EXTRACT(DAY FROM CURRENT_DATE) > 5 THEN 
      DATE_TRUNC('MONTH', CURRENT_DATE) + INTERVAL '4 DAYS'
    ELSE 
      DATE_TRUNC('MONTH', CURRENT_DATE) - INTERVAL '1 MONTH' + INTERVAL '4 DAYS'
  END
WHERE 
  a.cert_stat_cd = '0'
  AND (a.biz_org = '8909' OR a.biz_org = '8939')
  AND a.medium_id NOT LIKE '62179108%'
  AND a.medium_id NOT LIKE '89%'
  AND a.medium_id NOT LIKE '6232%'
  AND a.primacct_open_dt >= '2020-01-01'
  AND a.primacct_open_dt <= '2020-12-31'
ORDER BY 
  a.biz_org, 
  a.cust_id, 
  a.medium_id, 
  a.primacct_open_dt;