# GraphRAG Actual PoC Report (2026-03-17)

## 범위
- managed active docs를 포함한 현재 markdown 집합에서 graph snapshot을 생성한다.
- graph-candidate 질문 6개를 대상으로 관계 확장 검색 latency와 expected entity coverage를 측정한다.
- 이번 측정은 answer generation이 아니라 sidecar retrieval viability 확인 1차다.

## Ingest Stats
- collection: `all`
- source_docs: `5`
- section_hits: `21`
- nodes: `20`
- edges: `48`

## Benchmark Summary
- questions: `6`
- avg_latency_ms: `0.068`
- avg_expected_entity_hit_ratio: `0.9444`
- max_hops: `2`

## Question Results
### GQ-09
- latency_ms: `0.08`
- expected_entity_hit_ratio: `1.0`
- query_entities: `enlightenment, newton, voltaire`
- matched_entities: `bologna_university, ecole_polytechnique, enlightenment, french_revolution, galileo, german_physical_society, great_fire_london, helmholtz, humboldt_university, leibniz, magnus_lab, medici, napoleonic_wars, newton, padua_university, royal_society, siemens, voltaire`
- sample_relations:
  - Newton <-> Voltaire | weight=3 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
  - Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
  - Enlightenment <-> Newton | weight=2 | ge.md: 2. 계몽주의 시대: 라이프니츠와 지적 네트워크의 정치학 (17세기 ~ 18세기)
### GQ-10
- latency_ms: `0.074`
- expected_entity_hit_ratio: `1.0`
- query_entities: `leibniz, newton`
- matched_entities: `bologna_university, ecole_polytechnique, enlightenment, french_revolution, galileo, german_physical_society, great_fire_london, helmholtz, humboldt_university, leibniz, magnus_lab, medici, napoleonic_wars, newton, padua_university, royal_society, siemens, voltaire`
- sample_relations:
  - Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
  - Newton <-> Voltaire | weight=3 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
  - Enlightenment <-> Newton | weight=2 | ge.md: 2. 계몽주의 시대: 라이프니츠와 지적 네트워크의 정치학 (17세기 ~ 18세기)
### GQ-12
- latency_ms: `0.069`
- expected_entity_hit_ratio: `1.0`
- query_entities: `german_physical_society, helmholtz, magnus_lab, siemens`
- matched_entities: `ecole_polytechnique, enlightenment, galileo, german_physical_society, great_fire_london, helmholtz, humboldt_university, leibniz, magnus_lab, medici, napoleonic_wars, newton, padua_university, royal_society, siemens, voltaire`
- sample_relations:
  - Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
  - Newton <-> Voltaire | weight=3 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
  - Helmholtz <-> Newton | weight=2 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
### GQ-14
- latency_ms: `0.075`
- expected_entity_hit_ratio: `1.0`
- query_entities: `french_revolution, great_fire_london, napoleonic_wars`
- matched_entities: `bologna_university, ecole_polytechnique, enlightenment, french_revolution, galileo, german_physical_society, great_fire_london, helmholtz, humboldt_university, leibniz, magnus_lab, medici, napoleonic_wars, newton, padua_university, royal_society, siemens, voltaire`
- sample_relations:
  - Newton <-> Voltaire | weight=3 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
  - Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
  - Ecole Polytechnique <-> French Revolution | weight=2 | eu_summry.md: 4. 프랑스(France): 절대 권력과 이성적 혁명
### GQ-15
- latency_ms: `0.085`
- expected_entity_hit_ratio: `1.0`
- query_entities: `ecole_polytechnique, humboldt_university, padua_university, royal_society`
- matched_entities: `bologna_university, ecole_polytechnique, enlightenment, french_revolution, galileo, german_physical_society, great_fire_london, helmholtz, humboldt_university, leibniz, magnus_lab, medici, napoleonic_wars, newton, padua_university, royal_society, siemens, voltaire`
- sample_relations:
  - Newton <-> Voltaire | weight=3 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
  - Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드리히 대왕의 어머니로서, 군인왕 아버지의 폭압 속에서도 아들에게 음악과 과학의 교양을 심어주어 '학문하는 군주'의 토대를 만들었습니다.
  - Great Fire of London <-> Royal Society | weight=2 | eu_summry.md: 2. 영국(United Kingdom): 혁명의 심장부와 소수의 헌신
### GQ-16
- latency_ms: `0.024`
- expected_entity_hit_ratio: `0.6667`
- query_entities: `gottingen, max_planck_institute`
- matched_entities: `gottingen, max_planck_institute`
- sample_relations:
  - Gottingen <-> Max Planck Institute | weight=1 | ge.md: 5. 지성의 정점과 위기: 괴팅겐의 황금기와 전후 재건 (20세기)

## 해석
- 이 결과는 graph snapshot 기반 관계 확장 검색이 현재 문서 집합에서 실제로 작동하는지 보는 1차 실측이다.
- `expected_entity_hit_ratio`는 answer 정확도가 아니라 관계 후보 recall 성격의 지표다.
- 현재 2-hop 확장은 일부 질문에서 그래프 전체로 넓게 퍼지므로 precision 측정은 아직 부족하다.
- answer quality의 최종 개선 여부는 아직 확인되지 않았고, 다음 단계에서 vector baseline과 answer-level 비교가 추가로 필요하다.
