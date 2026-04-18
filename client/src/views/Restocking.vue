<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking Planner</h2>
      <p>Enter a budget to get AI-optimized recommendations on which items to restock.</p>
    </div>

    <div class="card">
      <div class="input-row">
        <label class="input-label" for="budget-input">Budget</label>
        <div class="input-group">
          <span class="currency-prefix">$</span>
          <input
            id="budget-input"
            v-model="budget"
            type="number"
            min="1"
            step="100"
            placeholder="e.g. 25000"
            class="budget-input"
            @keyup.enter="calculate"
          />
        </div>
        <button
          class="btn-primary"
          :disabled="loading"
          @click="calculate"
        >
          Generate Recommendations
        </button>
      </div>
      <div
        v-if="selectedLocation !== 'all' || selectedCategory !== 'all'"
        class="filter-info"
      >
        Filtering by:
        <span v-if="selectedLocation !== 'all'">{{ selectedLocation }}</span>
        <span v-if="selectedLocation !== 'all' && selectedCategory !== 'all'"> / </span>
        <span v-if="selectedCategory !== 'all'">{{ selectedCategory }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading recommendations...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-if="results">
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">Budget</div>
          <div class="summary-value">{{ formatCurrency(results.budget) }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Allocated</div>
          <div
            class="summary-value"
            :class="results.total_cost <= results.budget ? 'value-success' : 'value-danger'"
          >
            {{ formatCurrency(results.total_cost) }}
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Remaining</div>
          <div class="summary-value">{{ formatCurrency(results.remaining_budget) }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Items to Order</div>
          <div class="summary-value">{{ results.items_count }}</div>
        </div>
      </div>

      <div v-if="results.recommendations.length === 0" class="card empty-state">
        All items are adequately stocked for this budget. Try reducing the budget or adjusting filters.
      </div>

      <div v-else class="card">
        <div class="card-header">
          <h3 class="card-title">Recommendations</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Priority</th>
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Warehouse</th>
                <th class="col-right">On Hand</th>
                <th class="col-right">Reorder Pt</th>
                <th class="col-right">Units to Order</th>
                <th class="col-right">Unit Cost</th>
                <th class="col-right">Subtotal</th>
                <th>Demand Trend</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in results.recommendations" :key="item.sku">
                <td>
                  <span :class="['badge', priorityClass(item.priority)]">{{ item.priority }}</span>
                </td>
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ item.name }}</td>
                <td>{{ item.category }}</td>
                <td>{{ item.warehouse }}</td>
                <td class="col-right">{{ item.quantity_on_hand }}</td>
                <td class="col-right">{{ item.reorder_point }}</td>
                <td class="col-right"><strong>{{ item.recommended_quantity }}</strong></td>
                <td class="col-right">{{ formatCurrency(item.unit_cost) }}</td>
                <td class="col-right"><strong>{{ formatCurrency(item.subtotal) }}</strong></td>
                <td :class="trendClass(item.demand_trend)">{{ trendLabel(item.demand_trend) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="results.suggestions.length > 0" class="suggestions-callout">
        <div class="suggestions-header">
          <div class="suggestions-title">
            <span class="warning-icon">&#9650;</span>
            Consider increasing your budget
          </div>
          <button class="btn-toggle" @click="showSuggestions = !showSuggestions">
            {{ showSuggestions ? 'Hide' : 'Show' }}
          </button>
        </div>
        <div class="suggestions-summary">
          {{ results.suggestions.length }} more item(s) could not be included.
          Minimum additional budget needed:
          {{ formatCurrency(results.suggestions.reduce((sum, s) => sum + s.min_budget_needed, 0)) }}
        </div>
        <div v-show="showSuggestions" class="suggestions-list">
          <div
            v-for="s in results.suggestions"
            :key="s.sku"
            class="suggestion-row"
          >
            <span :class="['badge', priorityClass(s.priority)]">{{ s.priority }}</span>
            <span class="suggestion-name">{{ s.name }} <span class="suggestion-sku">({{ s.sku }})</span></span>
            <span class="suggestion-cost">Min to include: {{ formatCurrency(s.min_budget_needed) }}</span>
            <span class="suggestion-sep">|</span>
            <span class="suggestion-cost">Full restock: {{ formatCurrency(s.full_restock_cost) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { ref, watch } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'

export default {
  name: 'Restocking',
  setup() {
    const budget = ref('')
    const results = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const showSuggestions = ref(false)

    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const calculate = async () => {
      const b = parseFloat(budget.value)
      if (!b || b <= 0) {
        error.value = 'Please enter a valid budget greater than $0'
        return
      }
      loading.value = true
      error.value = null
      results.value = null
      try {
        const filters = getCurrentFilters()
        results.value = await api.getRestockingRecommendations(b, filters)
      } catch (err) {
        error.value = 'Failed to generate recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      if (results.value !== null) {
        calculate()
      }
    })

    const formatCurrency = (val) =>
      '$' + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

    const priorityClass = (p) =>
      p === 'critical' ? 'danger' : p === 'high' ? 'warning' : 'info'

    const trendClass = (t) =>
      t === 'increasing' ? 'trend-up' : t === 'decreasing' ? 'trend-down' : 'trend-stable'

    const trendLabel = (t) =>
      t ? t.charAt(0).toUpperCase() + t.slice(1) : '—'

    return {
      budget,
      results,
      loading,
      error,
      showSuggestions,
      selectedLocation,
      selectedCategory,
      calculate,
      formatCurrency,
      priorityClass,
      trendClass,
      trendLabel
    }
  }
}
</script>

<style scoped>
.restocking {
  padding-bottom: 2rem;
}

/* Input card */
.input-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.input-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: #475569;
}

.input-group {
  display: flex;
  align-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  overflow: hidden;
  transition: border-color 0.2s;
}

.input-group:focus-within {
  border-color: #3b82f6;
  background: white;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.currency-prefix {
  padding: 0 0.5rem 0 0.75rem;
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
  user-select: none;
}

.budget-input {
  border: none;
  outline: none;
  background: transparent;
  padding: 0.5rem 0.75rem 0.5rem 0;
  font-size: 0.875rem;
  color: #0f172a;
  width: 160px;
}

.budget-input::placeholder {
  color: #94a3b8;
}

/* Remove spinner arrows on number input */
.budget-input::-webkit-outer-spin-button,
.budget-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.budget-input[type=number] {
  -moz-appearance: textfield;
}

.btn-primary {
  padding: 0.5rem 1.25rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-info {
  margin-top: 0.75rem;
  font-size: 0.813rem;
  color: #64748b;
}

/* Summary grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.summary-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.25rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.value-success {
  color: #059669;
}

.value-danger {
  color: #dc2626;
}

/* Table numeric alignment */
.col-right {
  text-align: right;
}

/* Demand trend text colors */
.trend-up {
  color: #059669;
  font-weight: 500;
}

.trend-down {
  color: #dc2626;
  font-weight: 500;
}

.trend-stable {
  color: #94a3b8;
}

/* Empty state */
.empty-state {
  color: #64748b;
  font-size: 0.938rem;
  padding: 2rem;
  text-align: center;
}

/* Suggestions callout */
.suggestions-callout {
  border: 1px solid #ca8a04;
  background: rgba(234, 179, 8, 0.06);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-top: 1.25rem;
}

.suggestions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.suggestions-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.938rem;
  color: #92400e;
}

.warning-icon {
  font-size: 0.75rem;
  color: #d97706;
}

.btn-toggle {
  padding: 0.25rem 0.75rem;
  font-size: 0.813rem;
  font-weight: 600;
  color: #92400e;
  background: transparent;
  border: 1px solid #ca8a04;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-toggle:hover {
  background: rgba(234, 179, 8, 0.12);
}

.suggestions-summary {
  font-size: 0.875rem;
  color: #78716c;
  margin-bottom: 0.5rem;
}

.suggestions-list {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.suggestion-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
  flex-wrap: wrap;
}

.suggestion-name {
  font-weight: 500;
  color: #0f172a;
  flex: 1;
  min-width: 160px;
}

.suggestion-sku {
  font-weight: 400;
  color: #94a3b8;
  font-size: 0.813rem;
}

.suggestion-cost {
  color: #475569;
  white-space: nowrap;
}

.suggestion-sep {
  color: #cbd5e1;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 500px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
