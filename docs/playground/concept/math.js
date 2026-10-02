/* Worked-example arithmetic. Real queries are evaluated by Prometheus, not this module. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AcademyMath = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  function counterChange(values) {
    return values.slice(1).reduce((total, value, i) => total + (value >= values[i] ? value - values[i] : value), 0);
  }
  function rateExample(lastIncrement = 60) {
    const values = [100, 110, 120, 130, 130 + Number(lastIncrement)];
    const change = counterChange(values);
    return {values, change, span: 60, window: 75, rate: change / 60, irate: Number(lastIncrement) / 15, increase: change / 60 * 75};
  }
  function overTime(values, fn) {
    if (!values.length) return NaN;
    const sum = values.reduce((a, b) => a + b, 0);
    switch (fn) {
      case 'sum_over_time': return sum;
      case 'avg_over_time': return sum / values.length;
      case 'min_over_time': return Math.min(...values);
      case 'max_over_time': return Math.max(...values);
      case 'count_over_time': return values.length;
      default: throw new Error('Unknown over-time function');
    }
  }
  function buckets(values, bounds = [.1, .5, 1, Infinity]) {
    return bounds.map(bound => values.filter(value => value <= bound).length);
  }
  function quantile(q, counts = [20, 60, 90, 100, 100], bounds = [.1, .5, 1, 2, Infinity]) {
    const rank = q * counts[counts.length - 1];
    const index = counts.findIndex(count => count >= rank);
    const lower = index > 0 ? bounds[index - 1] : 0;
    const upper = bounds[index];
    const before = index > 0 ? counts[index - 1] : 0;
    const after = counts[index];
    const value = upper === Infinity ? lower : lower + (upper - lower) * (after === before ? 0 : (rank - before) / (after - before));
    return {value, rank, index, lower, upper, before, after};
  }
  return {counterChange, rateExample, overTime, buckets, quantile};
});
