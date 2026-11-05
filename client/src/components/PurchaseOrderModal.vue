<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- View mode -->
          <template v-if="mode === 'view'">
            <div class="modal-body">
              <div v-if="loadingPO" class="state-message">{{ t('purchaseOrder.loading') }}</div>
              <div v-else-if="loadError" class="error-message">{{ loadError }}</div>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.poId') }}</div>
                  <div class="info-value mono">{{ purchaseOrder.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value"><span class="badge">{{ purchaseOrder.status }}</span></div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ purchaseOrder.quantity }} {{ t('purchaseOrder.units') }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ formatUnitCost(purchaseOrder.unit_cost) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ formatMoney(purchaseOrder.quantity * purchaseOrder.unit_cost) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                </div>
                <div class="info-item full-width">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value notes">{{ purchaseOrder.notes || t('purchaseOrder.noNotes') }}</div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            </div>
          </template>

          <!-- Create mode -->
          <form v-else novalidate @submit.prevent="submit" class="po-form">
            <div class="modal-body">
              <div class="summary-box">
                <div class="summary-title">{{ t('purchaseOrder.shortageSummary') }}</div>
                <div class="info-grid">
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.item') }}</div>
                    <div class="info-value">{{ translateProductName(backlogItem.item_name) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.sku') }}</div>
                    <div class="info-value mono">{{ backlogItem.item_sku }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.orderId') }}</div>
                    <div class="info-value mono">{{ backlogItem.order_id }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.quantityNeeded') }}</div>
                    <div class="info-value">{{ backlogItem.quantity_needed }} {{ t('purchaseOrder.units') }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.quantityAvailable') }}</div>
                    <div class="info-value">{{ backlogItem.quantity_available }} {{ t('purchaseOrder.units') }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.shortage') }}</div>
                    <div class="info-value danger-text">{{ shortage }} {{ t('purchaseOrder.units') }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.daysDelayed') }}</div>
                    <div class="info-value">{{ backlogItem.days_delayed }} {{ t('purchaseOrder.days') }}</div>
                  </div>
                </div>
              </div>

              <div class="form-grid">
                <div class="form-field full-width">
                  <label for="po-supplier">{{ t('purchaseOrder.supplierName') }} *</label>
                  <input id="po-supplier" v-model="form.supplier_name" type="text" :disabled="submitting" />
                </div>
                <div class="form-field">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }} *</label>
                  <input id="po-quantity" v-model.number="form.quantity" type="number" min="1" step="1" :disabled="submitting" />
                </div>
                <div class="form-field">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }} *</label>
                  <input id="po-unit-cost" v-model.number="form.unit_cost" type="number" min="0" step="0.01" :disabled="submitting" />
                </div>
                <div class="form-field full-width">
                  <label for="po-date">{{ t('purchaseOrder.expectedDelivery') }} *</label>
                  <input id="po-date" v-model="form.expected_delivery_date" type="date" :disabled="submitting" />
                </div>
                <div class="form-field full-width">
                  <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                  <textarea id="po-notes" v-model="form.notes" rows="3" :placeholder="t('purchaseOrder.notesPlaceholder')" :disabled="submitting"></textarea>
                </div>
              </div>

              <div class="total-row">
                <span class="info-label">{{ t('purchaseOrder.total') }}</span>
                <span class="total-value">{{ formatMoney(total) }}</span>
              </div>

              <div v-if="submitError" class="error-message" role="alert">{{ submitError }}</div>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-secondary" :disabled="submitting" @click="close">{{ t('common.cancel') }}</button>
              <button type="submit" class="btn-primary" :disabled="submitting">
                {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentCurrency, translateProductName } = useI18n()

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: {
    type: String,
    default: 'create',
    validator: (v) => ['create', 'view'].includes(v)
  }
})

const emit = defineEmits(['close', 'po-created'])

const form = reactive({
  supplier_name: '',
  quantity: 1,
  unit_cost: null,
  expected_delivery_date: '',
  notes: ''
})
const submitting = ref(false)
const submitError = ref(null)
const purchaseOrder = ref(null)
const loadingPO = ref(false)
const loadError = ref(null)

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return Math.max(props.backlogItem.quantity_needed - props.backlogItem.quantity_available, 0)
})

const total = computed(() => {
  const q = Number(form.quantity)
  const c = Number(form.unit_cost)
  return Number.isFinite(q) && Number.isFinite(c) ? q * c : 0
})

const formatMoney = (amount) => formatCurrency(amount, currentCurrency.value)
const formatUnitCost = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const resetForm = () => {
  form.supplier_name = ''
  form.quantity = shortage.value > 0 ? shortage.value : 1
  form.unit_cost = null
  form.expected_delivery_date = ''
  form.notes = ''
  submitting.value = false
  submitError.value = null
}

const loadPO = async () => {
  purchaseOrder.value = null
  loadError.value = null
  loadingPO.value = true
  try {
    purchaseOrder.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    loadError.value = err.response?.data?.detail || t('purchaseOrder.loadFailed')
    console.error('Failed to load purchase order:', err)
  } finally {
    loadingPO.value = false
  }
}

// Reset / load every time the modal opens
watch(
  () => props.isOpen,
  (open) => {
    if (!open || !props.backlogItem) return
    if (props.mode === 'view') loadPO()
    else resetForm()
  },
  { immediate: true }
)

const validate = () => {
  if (!form.supplier_name.trim()) return t('purchaseOrder.errors.supplierRequired')
  if (!(Number(form.quantity) > 0)) return t('purchaseOrder.errors.quantityInvalid')
  if (!(Number(form.unit_cost) > 0)) return t('purchaseOrder.errors.unitCostInvalid')
  if (!form.expected_delivery_date) return t('purchaseOrder.errors.dateRequired')
  return null
}

const submit = async () => {
  if (submitting.value) return
  const validationError = validate()
  if (validationError) {
    submitError.value = validationError
    return
  }
  submitting.value = true
  submitError.value = null
  try {
    const po = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.supplier_name.trim(),
      quantity: Number(form.quantity),
      unit_cost: Number(form.unit_cost),
      expected_delivery_date: form.expected_delivery_date,
      notes: form.notes.trim() || null
    })
    emit('po-created', po)
  } catch (err) {
    // 404 (unknown item) / 409 (PO exists) carry a readable `detail`
    const detail = err.response?.data?.detail
    submitError.value = typeof detail === 'string' ? detail : t('purchaseOrder.errors.createFailed')
    console.error('Failed to create purchase order:', err)
  } finally {
    submitting.value = false
  }
}

const close = () => {
  if (submitting.value) return
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 720px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.shortage-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1.5rem;
}

.shortage-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.shortage-title-section {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.item-sku {
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.priority-badge {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  flex-shrink: 0;
}

.priority-badge.high {
  background: #fecaca;
  color: #991b1b;
}

.priority-badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.priority-badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.shortage-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  padding: 1.25rem;
  border-radius: 10px;
  border: 2px solid;
}

.summary-card.danger {
  border-color: #fecaca;
  background: #fef2f2;
}

.summary-card.warning {
  border-color: #fed7aa;
  background: #fffbeb;
}

.summary-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
}

.summary-card.danger .summary-value {
  color: #dc2626;
}

.summary-card.warning .summary-value {
  color: #f59e0b;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.info-value.order-id,
.info-value.sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.po-form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.summary-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}

.summary-title {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 1rem;
}

.info-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.info-value.notes {
  white-space: pre-wrap;
}

.danger-text {
  color: #dc2626;
}

.full-width {
  grid-column: 1 / -1;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  background: #dbeafe;
  color: #1e40af;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #334155;
}

.form-field input,
.form-field textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.875rem;
  font-family: inherit;
  color: #0f172a;
  background: white;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.15);
}

.form-field input:disabled,
.form-field textarea:disabled {
  background: #f1f5f9;
  color: #64748b;
}

.total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.total-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.875rem;
}

.state-message {
  color: #64748b;
  text-align: center;
  padding: 2rem 0;
}

.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #0f172a;
  border: 1px solid #0f172a;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
