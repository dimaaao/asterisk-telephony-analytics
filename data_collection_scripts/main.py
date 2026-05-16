import pandas as pd
import pymysql
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta

# ===== CONFIG =====
PROJECT_ID = "YOUR_PROJECT_ID"
DATASET = "telephony"

TABLE = f"{PROJECT_ID}.{DATASET}.raw_cdr"
STAGING = f"{PROJECT_ID}.{DATASET}.staging_cdr"

MODE = "incremental"   # turned_off | incremental | history

DATE_FROM = "2026-04-23"
DATE_TO = "2026-04-24"

SERVICE_ACCOUNT_FILE = "YOUR_PATH"

# ===== BQ =====
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

# ===== MySQL =====
conn = pymysql.connect(
    host="YOUR_IP",
    user="YOUR_USER",
    password="YOUR_PASSWORD",
    database="YOUR_DATABASE",
    port=YOUR_PORT
)

# ===== функция загрузки =====
def load_and_merge(df, day_label=None):
    if df.empty:
        print(f"[{day_label}] нет данных")
        return

    print(f"[{day_label}] строк из MySQL: {len(df)}")

    df = df.astype(str)

    # staging
    client.delete_table(STAGING, not_found_ok=True)
    client.load_table_from_dataframe(df, STAGING).result()

    # merge
    merge_sql = f"""
    MERGE `{TABLE}` T
    USING `{STAGING}` S
    ON T.uniqueid = S.uniqueid
    AND T.sequence = S.sequence

    WHEN MATCHED THEN UPDATE SET
      calldate = S.calldate,
      clid = S.clid,
      src = S.src,
      dst = S.dst,
      dcontext = S.dcontext,
      channel = S.channel,
      dstchannel = S.dstchannel,
      lastapp = S.lastapp,
      lastdata = S.lastdata,
      duration = S.duration,
      billsec = S.billsec,
      disposition = S.disposition,
      amaflags = S.amaflags,
      accountcode = S.accountcode,
      userfield = S.userfield,
      did = S.did,
      recordingfile = S.recordingfile,
      cnum = S.cnum,
      cnam = S.cnam,
      outbound_cnum = S.outbound_cnum,
      outbound_cnam = S.outbound_cnam,
      dst_cnam = S.dst_cnam,
      linkedid = S.linkedid,
      peeraccount = S.peeraccount,
      sequence = S.sequence

    WHEN NOT MATCHED THEN
    INSERT ROW
    """

    client.query(merge_sql).result()

    print(f"[{day_label}] загружено в BQ: {len(df)}")


# ===== main =====

if MODE == "turned_off":
    print("⛔ выключено")

elif MODE == "incremental":
    print("=== INCREMENTAL ===")

    query = """
    SELECT *
    FROM cdr
    WHERE calldate >= NOW() - INTERVAL 8 HOUR
    """

    df = pd.read_sql(query, conn)
    print(f"Строк за 8 часов: {len(df)}")

    load_and_merge(df, "incremental")


elif MODE == "history":
    print("=== HISTORY START ===")

    start = datetime.fromisoformat(DATE_FROM)
    end = datetime.fromisoformat(DATE_TO)

    total_rows = 0
    days_processed = 0

    current = start

    while current < end:
        next_day = current + timedelta(days=1)
        day_label = current.date()

        print(f"\n📅 Обработка: {day_label}")

        query = f"""
        SELECT *
        FROM cdr
        WHERE calldate >= '{current}'
          AND calldate < '{next_day}'
        """

        df = pd.read_sql(query, conn)

        total_rows += len(df)
        days_processed += 1

        load_and_merge(df, day_label)

        current = next_day

    print("\n=== HISTORY DONE ===")
    print(f"Дней обработано: {days_processed}")
    print(f"Всего строк: {total_rows}")

else:
    print("неизвестный режим")
