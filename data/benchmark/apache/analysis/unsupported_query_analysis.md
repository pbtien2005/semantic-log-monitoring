# Unsupported Query Analysis: apache

- Query bank entries: 30
- Unsupported queries under current rules: 4
- Existing validation report found: yes

## Unsupported Queries

| query_id | category | filters | filtered_logs | candidate_patterns | frequent_terms | sample_messages | suggestion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| apache_q011 | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | init=1405, notice=1405, scoreboard=836, child=836, worker=569 | notice=2810, jk2_init=1672, found=1672, child=1672, scoreboard=1672, slot=1672, workerenv.init=1138, httpd=1138 | workerEnv.init() ok /etc/httpd/conf/workers2.properties / jk2_init() Found child 6725 in scoreboard slot 10 / jk2_init() Found child 6726 in scoreboard slot 8 | Review adding or strengthening pattern(s): init, notice, scoreboard, child, worker. |
| apache_q012 | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | init=1405, notice=1405, scoreboard=836, child=836, worker=569 | notice=2810, jk2_init=1672, found=1672, child=1672, scoreboard=1672, slot=1672, workerenv.init=1138, httpd=1138 | workerEnv.init() ok /etc/httpd/conf/workers2.properties / jk2_init() Found child 6725 in scoreboard slot 10 / jk2_init() Found child 6726 in scoreboard slot 8 | Review adding or strengthening pattern(s): init, notice, scoreboard, child, worker. |
| apache_q018 | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | init=1405, notice=1405, scoreboard=836, child=836, worker=569 | notice=2810, jk2_init=1672, found=1672, child=1672, scoreboard=1672, slot=1672, workerenv.init=1138, httpd=1138 | workerEnv.init() ok /etc/httpd/conf/workers2.properties / jk2_init() Found child 6725 in scoreboard slot 10 / jk2_init() Found child 6726 in scoreboard slot 8 | Review adding or strengthening pattern(s): init, notice, scoreboard, child, worker. |
| apache_q026 | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | init=1405, notice=1405, scoreboard=836, child=836, worker=569 | notice=2810, jk2_init=1672, found=1672, child=1672, scoreboard=1672, slot=1672, workerenv.init=1138, httpd=1138 | workerEnv.init() ok /etc/httpd/conf/workers2.properties / jk2_init() Found child 6725 in scoreboard slot 10 / jk2_init() Found child 6726 in scoreboard slot 8 | Review adding or strengthening pattern(s): init, notice, scoreboard, child, worker. |
