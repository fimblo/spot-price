#!/bin/bash

start=$(date "+%Y-%m-%d")
end="${start}T23:59:59"

cat<<EOF | sqlite3 -header -column database/spot_prices.db 
SELECT STRFTIME('%m/%d %H:%M', time_start) AS hour, kWh_SEK
    FROM spot_price
    WHERE
        DATETIME(time_start, '+0 hour') >= '$start'
        AND
        DATETIME(time_start, '+0 hour') < '$end'
    ORDER BY time_start ASC
EOF

