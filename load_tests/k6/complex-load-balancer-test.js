/**
 * Test load balancer avec endpoints complexes + Microservices Load Balancing
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';

const complexEndpointCalls = new Counter('complex_endpoint_calls');
const complexEndpointErrors = new Rate('complex_endpoint_errors');
const loadBalancerChecks = new Rate('load_balancer_checks');

const microservicesLBCalls = new Counter('microservices_lb_calls');
const microservicesLBDistribution = new Counter('microservices_lb_distribution');
const microservicesLBErrors = new Rate('microservices_lb_errors');
const cartInstanceResponseTime = new Trend('cart_instance_response_time');

export const options = {
  stages: [
    { duration: '30s', target: 3 },
    { duration: '1m', target: 8 },
    { duration: '2m', target: 15 },
    { duration: '1m', target: 25 },
    { duration: '30s', target: 8 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<4000', 'p(99)<6000'],
    'http_req_failed': ['rate<0.1'],
    'complex_endpoint_errors': ['rate<0.1'],
    'load_balancer_checks': ['rate>0.8'],
    'microservices_lb_errors': ['rate<0.05'],
    'microservices_lb_calls': ['count>50'],
    'cart_instance_response_time': ['p(95)<500']
  }
};

const BASE_URL = 'http://localhost:8080';
const API_TOKEN = 'pos-api-token-2025';
const API_KEY = 'pos-test-automation-dev-key-2025';  // Pour microservices

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json',
};

const microservicesHeaders = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json',
};

// Collecteur des stats par instance Cart Service
let instanceStats = {};

export default function () {
  let response = http.get(`${BASE_URL}/api/v1/stores/performances`, { headers });
  
  complexEndpointCalls.add(1);
  
  const performancesSuccess = check(response, {
    'lb stores performances status is 200': (r) => r.status === 200,
    'lb stores performances response time < 8s': (r) => r.timings.duration < 8000,
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

  // Test 1: Cart Service Load Balancing
  const sessionId = `lb_test_${__VU}_${Math.random().toString(36).substr(2, 9)}`;
  
  response = http.get(`${BASE_URL}/api/v1/cart?session_id=${sessionId}`, { headers: microservicesHeaders });
  
  microservicesLBCalls.add(1);
  
  const cartGetSuccess = check(response, {
    'cart lb get status is 200': (r) => r.status === 200,
    'cart lb response time < 500ms': (r) => r.timings.duration < 500,
    'cart lb has instance info': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.instance_info && data.instance_info.served_by;
      } catch {
        return false;
      }
    },
    'cart lb has load balancing headers': (r) => r.headers['X-Load-Balanced'] === 'true'
  });
  
  if (response.status === 200) {
    try {
      const data = JSON.parse(response.body);
      const instanceId = data.instance_info?.served_by || 'unknown';
      
      microservicesLBDistribution.add(1, { instance: instanceId });
      cartInstanceResponseTime.add(response.timings.duration, { instance: instanceId });
      
      if (!instanceStats[instanceId]) {
        instanceStats[instanceId] = { count: 0, totalTime: 0 };
      }
      instanceStats[instanceId].count++;
      instanceStats[instanceId].totalTime += response.timings.duration;
      
      microservicesLBErrors.add(0);
    } catch (e) {
      microservicesLBErrors.add(1);
    }
  } else {
    microservicesLBErrors.add(1);
  }
  
  sleep(0.5);
  
  // Test 2: Cart Service Add Item (POST) - Distribution
  const testProduct = { product_id: 1, quantity: 2, price: 29.99 };
  
  response = http.post(
    `${BASE_URL}/api/v1/cart?session_id=${sessionId}`,
    JSON.stringify(testProduct),
    { headers: microservicesHeaders }
  );
  
  microservicesLBCalls.add(1);
  
  const cartPostSuccess = check(response, {
    'cart lb post status is 200': (r) => r.status === 200,
    'cart lb post response time < 500ms': (r) => r.timings.duration < 500,
    'cart lb post has processed_by': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.instance_info && data.instance_info.processed_by;
      } catch {
        return false;
      }
    }
  });
  
  if (response.status === 200) {
    try {
      const data = JSON.parse(response.body);
      const instanceId = data.instance_info?.processed_by || 'unknown';
      microservicesLBDistribution.add(1, { instance: instanceId });
      cartInstanceResponseTime.add(response.timings.duration, { instance: instanceId });
      microservicesLBErrors.add(0);
    } catch (e) {
      microservicesLBErrors.add(1);
    }
  } else {
    microservicesLBErrors.add(1);
  }
  
  sleep(0.5);
  
  // Test 3: Cart Taxes Calculation - Distribution
  response = http.get(`${BASE_URL}/api/v1/cart/taxes?session_id=${sessionId}&province=QC`, { headers: microservicesHeaders });
  
  microservicesLBCalls.add(1);
  
  const cartTaxesSuccess = check(response, {
    'cart taxes lb status is 200': (r) => r.status === 200,
    'cart taxes lb has calculated_by': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.instance_info && data.instance_info.calculated_by;
      } catch {
        return false;
      }
    }
  });
  
  if (response.status === 200) {
    try {
      const data = JSON.parse(response.body);
      const instanceId = data.instance_info?.calculated_by || 'unknown';
      microservicesLBDistribution.add(1, { instance: instanceId });
      microservicesLBErrors.add(0);
    } catch (e) {
      microservicesLBErrors.add(1);
    }
  } else {
    microservicesLBErrors.add(1);
  }
  
  sleep(1);
  
  response = http.get(`${BASE_URL}/api/v1/reports/dashboard`, { headers });
  
  complexEndpointCalls.add(1);
  
  const dashboardSuccess = check(response, {
    'lb dashboard status is 200': (r) => r.status === 200,
    'lb dashboard response time < 8s': (r) => r.timings.duration < 8000,
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
  
  sleep(2);
  
  response = http.get(`${BASE_URL}/api/health`, { headers });
  
  const healthSuccess = check(response, {
    'lb api health status is 200': (r) => r.status === 200,
    'lb api health response time < 1s': (r) => r.timings.duration < 1000,
    'lb api health load balanced': (r) => r.headers['Server'] !== undefined || r.headers['server'] !== undefined,
  });
  
  loadBalancerChecks.add(healthSuccess ? 1 : 0);
  
  sleep(1);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  const enrichedReport = {
    ...data,
    microservices_load_balancing: {
      test_type: 'cart_service_multi_instance',
      instances_detected: Object.keys(instanceStats).length,
      instance_distribution: instanceStats,
      total_microservices_calls: data.metrics.microservices_lb_calls?.values?.count || 0,
      lb_error_rate: data.metrics.microservices_lb_errors?.values?.rate || 0,
      avg_cart_response_time: data.metrics.cart_instance_response_time?.values?.avg || 0
    }
  };
  
  console.log('\n=== Microservices Load Balancing Results (Étape 3) ===');
  console.log('Instance Distribution:');
  Object.entries(instanceStats).forEach(([instance, stats]) => {
    const avgTime = (stats.totalTime / stats.count).toFixed(2);
    console.log(`  ${instance}: ${stats.count} requests (${avgTime}ms avg)`);
  });
  
  return {
    [`load_test_results/complex_load_balancer_with_microservices_${timestamp}.json`]: JSON.stringify(enrichedReport, null, 2),
    stdout: '\nTests Lab 4 + Microservices Load Balancing terminés\n'
  };
} 