# Qrels Quality Audit: apache

- Review rows: 794
- Positive rows suspected: 80

## Per Query Label Counts

| query_id | positive | hard_negative | uncertain | patterns |
| --- | --- | --- | --- | --- |
| apache_q001 | 20 | 10 | 0 | error state=20 |
| apache_q002 | 20 | 10 | 0 | forbidden=20 |
| apache_q003 | 20 | 0 | 5 | ~error=20 |
| apache_q004 | 20 | 10 | 0 | error state=20 |
| apache_q005 | 20 | 10 | 0 | error state=20 |
| apache_q006 | 20 | 10 | 0 | forbidden=20 |
| apache_q007 | 20 | 10 | 5 | error state=20 |
| apache_q008 | 20 | 10 | 0 | error state=20 |
| apache_q009 | 20 | 10 | 0 | forbidden=20 |
| apache_q010 | 20 | 10 | 0 | forbidden=20 |
| apache_q011 | 0 | 0 | 0 |  |
| apache_q012 | 0 | 0 | 0 |  |
| apache_q013 | 20 | 10 | 0 | error state=20 |
| apache_q014 | 20 | 10 | 0 | error state=20 |
| apache_q015 | 20 | 0 | 5 | ~error=20 |
| apache_q016 | 20 | 10 | 0 | error state=20 |
| apache_q017 | 20 | 10 | 0 | forbidden=20 |
| apache_q018 | 0 | 0 | 0 |  |
| apache_q019 | 20 | 0 | 5 | ~error=20 |
| apache_q020 | 20 | 10 | 0 | error state=20 |
| apache_q021 | 20 | 10 | 0 | error state=20 |
| apache_q022 | 20 | 10 | 0 | forbidden=20 |
| apache_q023 | 20 | 10 | 5 | error state=20 |
| apache_q024 | 20 | 10 | 5 | error state=20 |
| apache_q025 | 20 | 10 | 5 | forbidden=20 |
| apache_q026 | 0 | 0 | 0 |  |
| apache_q027 | 20 | 10 | 5 | error state=20 |
| apache_q028 | 20 | 10 | 5 | forbidden=20 |
| apache_q029 | 20 | 10 | 0 | error state=20 |
| apache_q030 | 20 | 0 | 5 | ~error=20 |


## Top Suspected False Positives

| query_id | category | reason | message | suggestion |
| --- | --- | --- | --- | --- |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q003 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q015 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q019 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 7 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| apache_q030 | unknown | broad unknown positive: generic error/warn/exception requires review | mod_jk child workerEnv in error state 6 | Keep needs_review=true; avoid confident positives from generic error/warn only. |
