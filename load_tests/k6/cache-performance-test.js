/**
 * Test de performance du cache Redis avec endpoints complexes
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate } from 'k6/metrics';

const cacheHits = new Counter('cache_hits');
const cacheMisses = new Counter('cache_misses');
const cacheHitRate = new Rate('cache_hit_rate');
const complexEndpointCalls = new Counter('complex_endpoint_calls');
const complexEndpointErrors = new Rate('complex_endpoint_errors');

export const options = {
  stages: [
    { duration: '30s', target: 3 },
    { duration: '1m', target: 8 },
    { duration: '1m', target: 15 },
    { duration: '30s', target: 8 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<4000', 'p(99)<7000'],
    http_req_failed: ['rate<0.05'],
    cache_hit_rate: ['rate>0.2'],
    complex_endpoint_errors: ['rate<0.05'],
  },
};

const BASE_URL = 'http://localhost:8080';
const AUTH_TOKEN = 'pos-api-token-2025';

const headers = {
  'Authorization': `Bearer ${AUTH_TOKEN}`,
  'Content-Type': 'application/json',
};

export function setup() {
  const warmupResponse = http.get(`${BASE_URL}/api/cache/warm`, { headers });
  console.log('Cache warming initiated');
  sleep(2);
}

export default function () {
  let response = http.get(`${BASE_URL}/api/v1/stores/performances`, { headers });
  
  complexEndpointCalls.add(1);
  
  const performancesSuccess = check(response, {
    'cache stores performances status is 200': (r) => r.status === 200,
    'cache stores performances response time < 8s': (r) => r.timings.duration < 8000,
    'cache stores performances has data': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.data && Array.isArray(data.data);
      } catch {
        return false;
      }
    }
  });
  
  if (response.status !== 200) {
    complexEndpointErrors.add(1);
  } else {
    complexEndpointErrors.add(0);
  }

  if (response.status === 200) {
    if (response.timings.duration < 100) {
      cacheHits.add(1);
      cacheHitRate.add(true);
    } else {
      cacheMisses.add(1);
      cacheHitRate.add(false);
    }
  }
  
  sleep(2);
  
  response = http.get(`${BASE_URL}/api/v1/reports/dashboard`, { headers });
  
  complexEndpointCalls.add(1);
  
  const dashboardSuccess = check(response, {
    'cache dashboard status is 200': (r) => r.status === 200,
    'cache dashboard response time < 8s': (r) => r.timings.duration < 8000,
    'cache dashboard has indicators': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.indicateurs_magasins && Array.isArray(data.indicateurs_magasins);
      } catch {
        return false;
      }
    }
  });
  
  if (response.status !== 200) {
    complexEndpointErrors.add(1);
  } else {
    complexEndpointErrors.add(0);
  }
  
  if (response.status === 200) {
    if (response.timings.duration < 100) {
      cacheHits.add(1);
      cacheHitRate.add(true);
    } else {
      cacheMisses.add(1);
      cacheHitRate.add(false);
    }
  }
  
  sleep(3);
  
  response = http.get(`${BASE_URL}/api/health`, { headers });
  
  check(response, {
    'cache api health status is 200': (r) => r.status === 200,
    'cache api health response time < 1s': (r) => r.timings.duration < 1000,
  });
  
  sleep(1);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  const cacheStats = {
    cache_hits: data.metrics.cache_hits ? data.metrics.cache_hits.values.count : 0,
    cache_misses: data.metrics.cache_misses ? data.metrics.cache_misses.values.count : 0,
    cache_hit_rate: data.metrics.cache_hit_rate ? data.metrics.cache_hit_rate.values.rate : 0,
    avg_response_time: data.metrics.http_req_duration.values.avg,
    p95_response_time: data.metrics.http_req_duration.values['p(95)'],
    total_requests: data.metrics.http_reqs.values.count,
    requests_per_second: data.metrics.http_reqs.values.rate,
  };

  console.log('\nStatistiques du Cache:');
  console.log(`   Cache Hits: ${cacheStats.cache_hits}`);
  console.log(`   Cache Misses: ${cacheStats.cache_misses}`);
  console.log(`   Taux Hit Rate: ${(cacheStats.cache_hit_rate * 100).toFixed(2)}%`);
  console.log(`   Latence Moyenne: ${cacheStats.avg_response_time.toFixed(2)}ms`);
  console.log(`   Latence P95: ${cacheStats.p95_response_time.toFixed(2)}ms`);

  return {
    [`load_test_results/complex_cache_${timestamp}.json`]: JSON.stringify({
      summary: data,
      cache_metrics: cacheStats,
      timestamp: new Date().toISOString(),
    }, null, 2),
  };
} 