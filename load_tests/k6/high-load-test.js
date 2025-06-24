/**
 * Test load balancer avec HAUTE CHARGE (100 VUs)
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate } from 'k6/metrics';

const complexEndpointCalls = new Counter('complex_endpoint_calls');
const complexEndpointErrors = new Rate('complex_endpoint_errors');
const loadBalancerChecks = new Rate('load_balancer_checks');

export const options = {
  stages: [
    { duration: '1m', target: 25 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<10000', 'p(99)<15000'],
    'http_req_failed': ['rate<0.2'],
    'complex_endpoint_errors': ['rate<0.2'],
    'load_balancer_checks': ['rate>0.7'],
  }
};

const BASE_URL = 'http://localhost:8080';
const API_TOKEN = 'pos-api-token-2025';

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json',
};

export default function () {
  let response = http.get(`${BASE_URL}/api/v1/stores/performances`, { headers });
  
  complexEndpointCalls.add(1);
  
  const performancesSuccess = check(response, {
    'lb stores performances status is 200': (r) => r.status === 200,
    'lb stores performances response time < 15s': (r) => r.timings.duration < 15000, // Plus réaliste
    'lb stores performances has data': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.data && Array.isArray(data.data);
      } catch {
        return false;
      }
    },
    'lb has load balancer headers': (r) => r.headers['Server'] !== undefined || r.headers['server'] !== undefined,
  });
  
  if (response.status !== 200) {
    complexEndpointErrors.add(1);
  } else {
    complexEndpointErrors.add(0);
  }
  
  sleep(1);
  
  response = http.get(`${BASE_URL}/api/v1/reports/dashboard`, { headers });
  
  complexEndpointCalls.add(1);
  
  const dashboardSuccess = check(response, {
    'lb dashboard status is 200': (r) => r.status === 200,
    'lb dashboard response time < 15s': (r) => r.timings.duration < 15000,
    'lb dashboard has indicators': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.indicateurs_magasins && Array.isArray(data.indicateurs_magasins);
      } catch {
        return false;
      }
    },
    'lb dashboard load balanced': (r) => r.headers['Server'] !== undefined || r.headers['server'] !== undefined,
  });
  
  if (response.status !== 200) {
    complexEndpointErrors.add(1);
  } else {
    complexEndpointErrors.add(0);
  }
  
  sleep(1);
  
  response = http.get(`${BASE_URL}/api/health`, { headers });
  
  const healthSuccess = check(response, {
    'lb api health status is 200': (r) => r.status === 200,
    'lb api health response time < 2s': (r) => r.timings.duration < 2000,
    'lb api health load balanced': (r) => r.headers['Server'] !== undefined || r.headers['server'] !== undefined,
  });
  
  loadBalancerChecks.add(healthSuccess ? 1 : 0);
  
  sleep(0.5);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  return {
    [`load_test_results/high_load_lb_${timestamp}.json`]: JSON.stringify(data, null, 2),
  };
} 