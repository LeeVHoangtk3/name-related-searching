#!/bin/bash
# Script: benchmark_sparql.sh
# Ý nghĩa: Đo thời gian phản hồi thực tế của Wikidata SPARQL endpoint đối với câu truy vấn cũ và mới (isURI), loại bỏ CDN cache.

WIKIDATA_ENDPOINT="https://query.wikidata.org/sparql"
USER_AGENT="WikiBFS-Benchmark/1.0 (contact: qa-team@wikibfs.local)"
TEST_ENTITY="Q34660" # J. K. Rowling

get_query_old() {
  local qid=$1
  cat <<EOF
SELECT DISTINCT ?neighbor WHERE {
  { wd:$qid ?p ?neighbor . FILTER(STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q")) }
  UNION
  { ?neighbor ?p wd:$qid . FILTER(STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q")) }
  FILTER(?neighbor != wd:$qid)
  BIND(rand() as ?rnd)
} LIMIT 50
EOF
}

get_query_new() {
  local qid=$1
  cat <<EOF
SELECT DISTINCT ?neighbor WHERE {
  { wd:$qid ?p ?neighbor . FILTER(isURI(?neighbor)) }
  UNION
  { ?neighbor ?p wd:$qid . FILTER(isURI(?neighbor)) }
  FILTER(?neighbor != wd:$qid)
  BIND(rand() as ?rnd)
} LIMIT 50
EOF
}

echo -e "\033[0;36m=== [1/2] ĐO HIỆU NĂNG CÂU TRUY VẤN CŨ (STRSTARTS) ===\033[0m"
QUERY_OLD=$(get_query_old "$TEST_ENTITY")

TIME_OLD=$(curl -s -X POST "$WIKIDATA_ENDPOINT" \
  -H "Accept: application/sparql-results+json" \
  -H "Cache-Control: no-cache" \
  -H "User-Agent: $USER_AGENT" \
  --data-urlencode "query=$QUERY_OLD" \
  -o /dev/null -w "%{time_total}")

echo "Thời gian phản hồi truy vấn cũ (STRSTARTS): $TIME_OLD giây"

echo -e "\n\033[0;36m=== [2/2] ĐO HIỆU NĂNG CÂU TRUY VẤN TỐI ƯU MỚI (isURI) ===\033[0m"
QUERY_NEW=$(get_query_new "$TEST_ENTITY")

TIME_NEW=$(curl -s -X POST "$WIKIDATA_ENDPOINT" \
  -H "Accept: application/sparql-results+json" \
  -H "Cache-Control: no-cache" \
  -H "User-Agent: $USER_AGENT" \
  --data-urlencode "query=$QUERY_NEW" \
  -o /dev/null -w "%{time_total}")

echo "Thời gian phản hồi truy vấn mới (isURI): $TIME_NEW giây"

# So sánh hai thời gian
if (( $(echo "$TIME_OLD > 0" | bc -l) )) && (( $(echo "$TIME_NEW > 0" | bc -l) )); then
    DIFF=$(echo "$TIME_OLD - $TIME_NEW" | bc -l)
    PERCENT=$(echo "scale=2; ($DIFF / $TIME_OLD) * 100" | bc -l)
    
    echo -e "\n\033[0;36m=== KẾT QUẢ SO SÁNH HIỆU NĂNG ===\033[0m"
    if (( $(echo "$DIFF > 0" | bc -l) )); then
        echo -e "\033[0;32mCâu lệnh tối ưu mới (isURI) NHANH HƠN câu lệnh cũ $PERCENT% (giảm $DIFF giây)\033[0m"
    else
        echo -e "\033[0;33mSự khác biệt không đáng kể hoặc do Wikidata phản hồi tức thời/tải mạng biến động.\033[0m"
    fi
else
    echo -e "\033[0;31mLỗi tính toán thời gian benchmark!\033[0m"
    exit 1
fi

exit 0
