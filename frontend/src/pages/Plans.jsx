import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Pencil, Plus, Power } from 'lucide-react'
import {
  Button,
  Card,
  Field,
  Modal,
  PageHeader,
  PlanAvailability,
  SearchBar,
  Shell,
  Status,
} from '../components'
import { useAuth } from '../auth/AuthContext'
import {
  createPlan,
  formatApiError,
  listPlans,
  listProducts,
  setPlanStatus,
  updatePlan,
} from '../api'
import { formatPrice, intervalLabel } from '../format'

const EMPTY_FORM = {
  product_id: '',
  name: '',
  description: '',
  price: '',
  billing_interval: 'monthly',
  features: '',
}

function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <p className="mb-4 rounded-md bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600">
      {message}
    </p>
  )
}

export default function PlansPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [productFilter, setProductFilter] = useState('')
  const [intervalFilter, setIntervalFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [actionError, setActionError] = useState('')

  const { data: products = [] } = useQuery({
    queryKey: ['products', { includeInactive: true }],
    queryFn: () => listProducts({ include_inactive: true }),
  })

  const {
    data: plans = [],
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ['plans', { includeInactive: true }],
    queryFn: () => listPlans({ include_inactive: true }),
  })

  const saveMutation = useMutation({
    mutationFn: (payload) =>
      editing ? updatePlan(editing.id, payload) : createPlan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      setShowForm(false)
      setEditing(null)
      setForm(EMPTY_FORM)
      setFormError('')
    },
    onError: (err) => setFormError(formatApiError(err)),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => setPlanStatus(id, status),
    onSuccess: () => {
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    },
    onError: (err) => setActionError(formatApiError(err)),
  })

  const filtered = plans.filter((plan) => {
    const term = search.trim().toLowerCase()
    if (productFilter && String(plan.product_id) !== productFilter) return false
    if (intervalFilter && plan.billing_interval !== intervalFilter) return false
    if (!term) return true
    return [plan.name, plan.description, plan.product?.name]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(term)
  })

  const unavailableCount = plans.filter(
    (plan) => plan.product?.status === 'inactive',
  ).length
  const activeProducts = products.filter(
    (product) => product.status === 'active',
  )

  function openCreate() {
    setEditing(null)
    setForm({
      ...EMPTY_FORM,
      product_id: activeProducts.length ? String(activeProducts[0].id) : '',
    })
    setFormError('')
    setShowForm(true)
  }

  function openEdit(plan) {
    setEditing(plan)
    setForm({
      product_id: String(plan.product_id),
      name: plan.name,
      description: plan.description || '',
      price: plan.price,
      billing_interval: plan.billing_interval,
      features: (plan.features || []).map((feature) => feature.label).join('\n'),
    })
    setFormError('')
    setShowForm(true)
  }

  function closeForm() {
    if (saveMutation.isPending) return
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError('')
  }

  function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    if (!form.product_id) {
      setFormError('Select a product for this plan.')
      return
    }
    if (!editing && activeProducts.length === 0) {
      setFormError('An active product is required before an active plan can be created.')
      return
    }
    if (!form.name.trim()) {
      setFormError('Plan name is required.')
      return
    }
    if (form.price === '' || Number(form.price) < 0) {
      setFormError('Price must be zero or greater.')
      return
    }
    saveMutation.mutate({
      product_id: Number(form.product_id),
      name: form.name.trim(),
      description: form.description.trim() || null,
      price: form.price,
      billing_interval: form.billing_interval,
      features: form.features
        .split('\n')
        .map((label) => label.trim())
        .filter(Boolean),
    })
  }

  return (
    <Shell>
      <PageHeader
        title="Subscription Plans"
        action={
          isAdmin && (
            <Button onClick={openCreate}>
              <Plus size={14} />
              Add Plan
            </Button>
          )
        }
      />
      <Card>
        <div className="grid gap-3 sm:grid-cols-3">
          <SearchBar
            placeholder="Search plans..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <select
            className="field"
            value={productFilter}
            onChange={(event) => setProductFilter(event.target.value)}
          >
            <option value="">All products</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
          <select
            className="field"
            value={intervalFilter}
            onChange={(event) => setIntervalFilter(event.target.value)}
          >
            <option value="">All billing intervals</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <ErrorBanner
          message={actionError || (loadError && formatApiError(loadError))}
        />
        {unavailableCount > 0 && (
          <div className="mb-4 mt-4 flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <span>
              <b>
                {unavailableCount} plan{unavailableCount === 1 ? ' is' : 's are'} unavailable.
              </b>{' '}
              The associated product{unavailableCount === 1 ? ' is' : 's are'}{' '}
              inactive. This applies regardless of each plan's stored status;
              reactivate the product to restore availability for active plans.
            </span>
          </div>
        )}
        <div className="mt-5 overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Plan</th>
                <th>Product</th>
                <th>Price</th>
                <th>Billing Interval</th>
                <th>Features</th>
                <th>Plan Status</th>
                <th>Availability</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={isAdmin ? 8 : 7}>Loading plans...</td>
                </tr>
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 8 : 7}>No plans found.</td>
                </tr>
              )}
              {filtered.map((plan) => (
                <tr
                  key={plan.id}
                  className={
                    plan.product?.status === 'inactive'
                      ? 'plan-unavailable'
                      : undefined
                  }
                >
                  <td>
                    <span className="font-semibold">{plan.name}</span>
                    {plan.description && (
                      <span className="mt-1 block text-xs text-slate-500">
                        {plan.description}
                      </span>
                    )}
                  </td>
                  <td>
                    {plan.product?.name}
                    {plan.product?.status === 'inactive' && (
                      <span className="mt-1 flex items-center gap-1 text-xs font-semibold text-amber-700">
                        <AlertTriangle size={12} />
                        Product inactive
                      </span>
                    )}
                  </td>
                  <td className="font-medium">{formatPrice(plan.price)}</td>
                  <td>{intervalLabel(plan.billing_interval)}</td>
                  <td>
                    {plan.features?.length
                      ? `${plan.features.length} feature${
                          plan.features.length === 1 ? '' : 's'
                        }`
                      : '—'}
                  </td>
                  <td>
                    <Status>
                      {plan.status === 'active' ? 'Active' : 'Inactive'}
                    </Status>
                  </td>
                  <td>
                    <PlanAvailability plan={plan} />
                  </td>
                  {isAdmin && (
                    <td>
                      <button
                        type="button"
                        className="icon-button"
                        title="Edit plan"
                        onClick={() => openEdit(plan)}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        title={
                          plan.status === 'active'
                            ? 'Deactivate plan'
                            : 'Activate plan'
                        }
                        disabled={statusMutation.isPending}
                        onClick={() =>
                          statusMutation.mutate({
                            id: plan.id,
                            status:
                              plan.status === 'active' ? 'inactive' : 'active',
                          })
                        }
                      >
                        <Power size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal
        open={showForm}
        title={editing ? 'Edit Subscription Plan' : 'Add Subscription Plan'}
        onClose={closeForm}
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <ErrorBanner message={formError} />
          {!editing && activeProducts.length === 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              An active product is required before you can create an active
              subscription plan. Reactivate a product first.
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Product *">
              <select
                className="field"
                value={form.product_id}
                onChange={(event) =>
                  setForm({ ...form, product_id: event.target.value })
                }
              >
                <option value="">Select product</option>
                {products.map((product) => (
                  <option
                    key={product.id}
                    value={product.id}
                    disabled={!editing && product.status === 'inactive'}
                  >
                    {product.name}
                    {product.status === 'inactive' ? ' (inactive)' : ''}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Plan Name *">
              <input
                className="field"
                value={form.name}
                maxLength={150}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
              />
            </Field>
            <Field label="Price (INR) *">
              <input
                className="field"
                type="number"
                min="0"
                step="0.01"
                value={form.price}
                onChange={(event) =>
                  setForm({ ...form, price: event.target.value })
                }
              />
            </Field>
            <Field label="Billing Interval *">
              <select
                className="field"
                value={form.billing_interval}
                onChange={(event) =>
                  setForm({ ...form, billing_interval: event.target.value })
                }
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </Field>
            <Field label="Description">
              <textarea
                className="field"
                style={{
                  height: 'auto',
                  minHeight: 72,
                  paddingTop: 8,
                  paddingBottom: 8,
                  resize: 'vertical',
                }}
                maxLength={2000}
                value={form.description}
                onChange={(event) =>
                  setForm({ ...form, description: event.target.value })
                }
              />
            </Field>
            <Field label="Features" hint="One feature per line.">
              <textarea
                className="field"
                style={{
                  height: 'auto',
                  minHeight: 96,
                  paddingTop: 8,
                  paddingBottom: 8,
                  resize: 'vertical',
                }}
                value={form.features}
                onChange={(event) =>
                  setForm({ ...form, features: event.target.value })
                }
              />
            </Field>
          </div>
          <div className="flex justify-end gap-2 border-t border-[#edf0f5] pt-4">
            <button
              type="button"
              className="rounded-md border border-[#dce0ec] px-3 py-2 text-xs font-semibold text-slate-600"
              onClick={closeForm}
              disabled={saveMutation.isPending}
            >
              Cancel
            </button>
            <Button
              type="submit"
              disabled={saveMutation.isPending || (!editing && activeProducts.length === 0)}
            >
              {saveMutation.isPending ? 'Saving...' : 'Save Plan'}
            </Button>
          </div>
        </form>
      </Modal>
    </Shell>
  )
}
