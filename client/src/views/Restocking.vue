<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-row">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budgetLabel') }}</label>
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          min="0"
          :max="maxBudget"
          step="100"
          class="budget-slider"
          :disabled="candidates.length === 0"
        />
        <p class="budget-hint">{{ t('restocking.budgetHint') }}</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.summary.totalCost') }}</div>
          <div class="stat-value">{{ money(totalCost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.remainingBudget') }}</div>
          <div class="stat-value">{{ money(remainingBudget) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.itemCount') }}</div>
          <div class="stat-value">{{ recommended.length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.longestLeadTime') }}</div>
          <div class="stat-value">{{ t('restocking.daysValue', { count: longestLeadTime }) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedHeading') }} ({{ recommended.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="recommended.length === 0 || submitting || !!confirmation"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="confirmation" class="notice notice-success">
          <strong>{{ t('restocking.successTitle') }}</strong>
          <span>
            {{ t('restocking.successMessage', {
              orderNumber: confirmation.order_number,
              days: confirmation.lead_time_days,
              date: formatDate(confirmation.expected_delivery)
            }) }}
          </span>
          <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="submitError" class="notice notice-error">{{ submitError }}</div>

        <div v-if="candidates.length === 0" class="empty-state">{{ t('restocking.empty') }}</div>
        <div v-else-if="recommended.length === 0" class="empty-state">{{ t('restocking.nothingFits') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommended" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ item.name }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td>{{ item.quantity }}</td>
                <td>{{ money(item.unit_cost) }}</td>
                <td><strong>{{ money(item.lineTotal) }}</strong></td>
                <td>{{ item.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="notIncluded.length > 0" class="card not-included">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.notIncludedHeading') }} ({{ notIncluded.length }})</h3>
        </div>
        <div class="table-container">
          <table class="compact-table">
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in notIncluded" :key="item.sku">
                <td>{{ item.sku }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ money(item.lineTotal) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const submitError = ref(null)
    const confirmation = ref(null)

    const money = (amount) => formatCurrency(amount, currentCurrency.value)

    const trendRank = { increasing: 0, stable: 1, decreasing: 2 }

    // Only items whose forecast exceeds current demand need restocking;
    // decreasing items have a non-positive gap and drop out here.
    const candidates = computed(() => {
      return forecasts.value
        .map(f => {
          const gap = f.forecasted_demand - f.current_demand
          return {
            sku: f.item_sku,
            name: f.item_name,
            trend: f.trend,
            quantity: gap,
            unit_cost: f.unit_cost,
            lead_time_days: f.lead_time_days,
            // Rounded to cents so budget comparisons aren't thrown off by float
            // error (150 * 24.99 is 3748.5000000000005) and match the server's total.
            lineTotal: Math.round(gap * f.unit_cost * 100) / 100
          }
        })
        .filter(c => c.quantity > 0)
        .sort((a, b) => {
          const rankDiff = (trendRank[a.trend] ?? 3) - (trendRank[b.trend] ?? 3)
          return rankDiff !== 0 ? rankDiff : b.quantity - a.quantity
        })
    })

    // Slider ceiling: sum of every candidate's line total, rounded up to the next 500
    const maxBudget = computed(() => {
      const sum = candidates.value.reduce((acc, c) => acc + c.lineTotal, 0)
      return Math.ceil(sum / 500) * 500
    })

    // Greedy priority fill, NOT a strict top-N. Candidates are already in priority
    // order; we take each one that fits the remaining budget. When an item does not
    // fit we skip it and keep iterating (rather than stopping), because a cheaper,
    // lower-priority item later in the list may still fit and use up leftover budget.
    const split = computed(() => {
      // Track the remaining budget in integer cents; repeated float subtraction
      // would drift and could wrongly exclude an item that exactly fits.
      let remainingCents = Math.round(budget.value * 100)
      const included = []
      const excluded = []
      for (const c of candidates.value) {
        const lineCents = Math.round(c.lineTotal * 100)
        if (lineCents <= remainingCents) {
          included.push(c)
          remainingCents -= lineCents
        } else {
          excluded.push(c)
        }
      }
      return { included, excluded }
    })

    const recommended = computed(() => split.value.included)
    const notIncluded = computed(() => split.value.excluded)

    const totalCost = computed(() => recommended.value.reduce((acc, r) => acc + r.lineTotal, 0))
    const remainingBudget = computed(() => budget.value - totalCost.value)
    const longestLeadTime = computed(() => {
      return recommended.value.reduce((max, r) => Math.max(max, r.lead_time_days || 0), 0)
    })

    const formatDate = (value) => {
      if (!value) return '-'
      const d = new Date(value)
      if (isNaN(d.getTime())) return '-'
      return d.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        // Default the budget to the maximum so everything is selected initially
        budget.value = maxBudget.value
      } catch (err) {
        error.value = t('restocking.loadError') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (recommended.value.length === 0 || submitting.value) return
      submitting.value = true
      submitError.value = null
      confirmation.value = null
      try {
        confirmation.value = await api.createRestockingOrder({
          items: recommended.value.map(r => ({
            sku: r.sku,
            name: r.name,
            quantity: r.quantity,
            unit_cost: r.unit_cost,
            lead_time_days: r.lead_time_days
          })),
          budget: budget.value
        })
      } catch (err) {
        // A 400 carries a string detail; a 422 carries an array of validation
        // objects, which would render as "[object Object]", so fall back for those.
        const detail = err.response?.data?.detail
        submitError.value = typeof detail === 'string' ? detail : t('restocking.errorGeneric')
      } finally {
        submitting.value = false
      }
    }

    // A confirmation describes the selection that was just ordered. Once the budget
    // changes it no longer matches the screen, so clear it, which also re-enables
    // Place Order for the new selection.
    watch(budget, () => {
      confirmation.value = null
    })

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      budget,
      maxBudget,
      candidates,
      recommended,
      notIncluded,
      totalCost,
      remainingBudget,
      longestLeadTime,
      submitting,
      submitError,
      confirmation,
      money,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #3b82f6;
}

.budget-hint {
  margin: 0.5rem 0 0;
  font-size: 0.813rem;
  color: #64748b;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.notice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin: 0 1.5rem 1rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
}

.notice-success {
  background: #d1fae5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.notice-success a {
  color: #047857;
  font-weight: 600;
}

.notice-error {
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.empty-state {
  padding: 1.5rem;
  color: #64748b;
  font-size: 0.875rem;
}

.not-included {
  margin-top: 1.5rem;
}

.compact-table {
  font-size: 0.813rem;
  color: #64748b;
}
</style>
