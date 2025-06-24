/**
 * Test baseline avec endpoints complexes
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate } from 'k6/metrics';

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
    'http_req_duration': ['p(95)<6000', 'p(99)<10000'],
    'http_req_failed': ['rate<0.05'],
    'complex_endpoint_errors': ['rate<0.05'],
  }
};

const BASE_URL = 'http://localhost:8000';
const API_TOKEN = 'pos-api-token-2025';

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json',
};

export default function () {
  let response = http.get(`${BASE_URL}/api/v1/stores/performances`, { headers });
  
  complexEndpointCalls.add(1);
  
  const performancesSuccess = check(response, {
    'stores performances status is 200': (r) => r.status === 200,
    'stores performances response time < 8s': (r) => r.timings.duration < 8000,
    'stores performances has data': (r) => {
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
  
  sleep(2);
  
  response = http.get(`${BASE_URL}/api/v1/reports/dashboard`, { headers });
  
  complexEndpointCalls.add(1);
  
  const dashboardSuccess = check(response, {
    'dashboard status is 200': (r) => r.status === 200,
    'dashboard response time < 8s': (r) => r.timings.duration < 8000,
    'dashboard has indicators': (r) => {
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
  
  sleep(3);
  
  response = http.get(`${BASE_URL}/api/health`, { headers });
  
  check(response, {
    'health status is 200': (r) => r.status === 200,
    'health response time < 1s': (r) => r.timings.duration < 1000,
  });
  
  sleep(1);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  return {
    [`load_test_results/complex_baseline_${timestamp}.json`]: JSON.stringify(data, null, 2),
  };
} 