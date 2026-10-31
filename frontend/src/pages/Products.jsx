import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Power } from 'lucide-react'
import {
  Button,
  Card,
  Field,
  Modal,
  PageHeader,
  SearchBar,
  Shell,
  Status,
} from '../components'
import { useAuth } from '../auth/AuthContext'
import {
  createProduct,
  formatApiError,
  listProducts,
  setProductStatus,
  updateProduct,
} from '../api'
import { formatPrice } from '../format'

const EMPTY_FORM = {
  name: '',
  description: '',
  product_type: '',
  base_price: '',
}

function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <p className="mb-3 rounded-md bg-rose-50 px-3 py-2 text-[10px] font-semibold text-rose-600">
      {message}
    </p>
  )
}

export default function ProductsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [actionError, setActionError] = useState('')

  const {
    data: products = [],
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ['products', { includeInactive: true }],
    queryFn: () => listProducts({ include_inactive: true }),
  })

  const saveMutation = useMutation({
    mutationFn: (payload) =>
      editing ? updateProduct(editing.id, payload) : createProduct(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      setShowForm(false)
      setEditing(null)
      setForm(EMPTY_FORM)
      setFormError('')
    },
    onError: (err) => setFormError(formatApiError(err)),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => setProductStatus(id, status),
    onSuccess: () => {
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    },
    onError: (err) => setActionError(formatApiError(err)),
  })

  const filtered = products.filter((product) => {
    const term = search.trim().toLowerCase()
    if (!term) return true
    return [product.name, product.product_type, product.description]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(term)
  })

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError('')
    setShowForm(true)
  }

  function openEdit(product) {
    setEditing(product)
    setForm({
      name: product.name,
      description: product.description || '',
      product_type: product.product_type || '',
      base_price: product.base_price,
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
    if (!form.name.trim()) {
      setFormError('Product name is required.')
      return
    }
    if (form.base_price === '' || Number(form.base_price) < 0) {
      setFormError('Base price must be zero or greater.')
      return
    }
    saveMutation.mutate({
      name: form.name.trim(),
      description: form.description.trim() || null,
      product_type: form.product_type.trim() || null,
      base_price: form.base_price,
    })
  }

  return (
    <Shell>
      <PageHeader
        title="Products"
        action={
          isAdmin && (
            <Button onClick={openCreate}>
              <Plus size={14} />
              Add Product
            </Button>
          )
        }
      />
      <Card>
        <SearchBar
          placeholder="Search products..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <ErrorBanner message={actionError || (loadError && formatApiError(loadError))} />
        <div className="mt-4 overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Type</th>
                <th>Base Price</th>
                <th>Status</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4}>Loading products...</td>
                </tr>
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4}>No products found.</td>
                </tr>
              )}
              {filtered.map((product) => (
                <tr key={product.id}>
                  <td>
                    <span className="font-semibold">{product.name}</span>
                    {product.description && (
                      <span className="block text-[9px] text-slate-400">
                        {product.description}
                      </span>
                    )}
                  </td>
                  <td>
                    {product.product_type ? (
                      <span className="chip">{product.product_type}</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{formatPrice(product.base_price)}</td>
                  <td>
                    <Status>
                      {product.status === 'active' ? 'Active' : 'Inactive'}
                    </Status>
                  </td>
                  {isAdmin && (
                    <td>
                      <button
                        type="button"
                        className="icon-button"
                        title="Edit product"
                        onClick={() => openEdit(product)}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        title={
                          product.status === 'active'
                            ? 'Deactivate product'
                            : 'Activate product'
                        }
                        disabled={statusMutation.isPending}
                        onClick={() =>
                          statusMutation.mutate({
                            id: product.id,
                            status:
                              product.status === 'active' ? 'inactive' : 'active',
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
        title={editing ? 'Edit Product' : 'Add Product'}
        onClose={closeForm}
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <ErrorBanner message={formError} />
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Product Name *">
              <input
                className="field"
                value={form.name}
                maxLength={150}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
              />
            </Field>
            <Field label="Type">
              <input
                className="field"
                value={form.product_type}
                maxLength={50}
                placeholder="Software / Service"
                onChange={(event) =>
                  setForm({ ...form, product_type: event.target.value })
                }
              />
            </Field>
            <Field label="Base Price (INR) *">
              <input
                className="field"
                type="number"
                min="0"
                step="0.01"
                value={form.base_price}
                onChange={(event) =>
                  setForm({ ...form, base_price: event.target.value })
                }
              />
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
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving...' : 'Save Product'}
            </Button>
          </div>
        </form>
      </Modal>
    </Shell>
  )
}
