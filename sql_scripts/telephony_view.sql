with raw_all_calls as (
  select
  linkedid,
  calldate,
  src,
  dst,
  channel,
  dstchannel,
  dcontext,
  lastapp,
  SAFE_CAST(duration as INT64) as duration,
  SAFE_CAST(billsec as INT64) as billsec,
  disposition,
  cnum,
  cnam,
  recordingfile
  from `YOUR_PROJECT.raw_cdr`
),

dict_managers as (select * from `YOUR_PROJECT.dict_managers`),


outgoing_calls as (
  select
    *,
    'outgoing_calls' as type_of_calls,
    1 as num_of_attempts,
    duration - billsec  as wait_time,
    case when disposition = 'ANSWERED' and billsec > 0 then 1 else null end as num_of_anwered_calls,
    case when disposition = 'ANSWERED' and billsec > 30 then 1 else null end as num_of_success_calls,
    CASE 
      WHEN cnam LIKE '%Call to%' OR cnam LIKE 'CB-%' 
        THEN REGEXP_EXTRACT(channel, r'(?:SIP|PJSIP)/(\d+)')
      ELSE cnum
    END AS manager_id,
  from raw_all_calls
    where dcontext = 'from-internal' and lastapp = 'Dial'
)


select
  u.*,
  date(calldate) as dt,
  m.manager
from outgoing_calls u
left join dict_managers m
on u.manager_id = m.number





