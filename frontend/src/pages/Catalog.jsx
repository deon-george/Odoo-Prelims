import { useQuery } from '@tanstack/react-query'
import { Card, PageHeader, Shell, Status } from '../components'
import { formatApiError, listPlans, listProducts } from '../api'
import { formatPrice, intervalLabel } from '../format'

export default function CatalogPage() {
  const productsQuery = useQuery({
    queryKey: ['catalog', 'products'],
    queryFn: () => listProducts(),
  })
  const plansQuery = useQuery({
    queryKey: ['catalog', 'plans'],
    queryFn: () => listPlans(),
  })

  const products = productsQuery.data || []
  const plans = plansQuery.data || []
  const error = productsQuery.error || plansQuery.error
  const isLoading = productsQuery.isLoading || plansQuery.isLoading

  return (
    <Shell customer>
      <PageHeader title="Product Catalog" />
      {error && (
        <p className="mb-3 rounded-md bg-rose-50 px-3 py-2 text-[10px] font-semibold text-rose-600">
          {formatApiError(error)}
        </p>
      )}
      {isLoading && (
        <Card>
          <p className="text-sm text-slate-500">Loading catalog...</p>
        </Card>
      )}
      {!isLoading && products.length === 0 && (
        <Card>
          <p className="text-sm text-slate-500">
            No products are currently available.
          </p>
        </Card>
      )}
      <div className="grid gap-4">
        {products.map((product) => {
          const productPlans = plans.filter(
            (plan) => plan.product_id === product.id,
          )
          return (
            <Card key={product.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <b className="text-sm">{product.name}</b>
                    {product.product_type && (
                      <span className="chip">{product.product_type}</span>
                    )}
                  </div>
                  {product.description && (
                    <p className="mt-1 text-[10px] text-slate-500">
                      {product.description}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-[9px] font-semibold text-slate-400">
                    BASE PRICE
                  </p>
                  <b className="text-sm">{formatPrice(product.base_price)}</b>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {productPlans.length === 0 && (
                  <p className="text-[10px] text-slate-400">
                    No plans are available for this product.
                  </p>
                )}
                {productPlans.map((plan) => (
                  <div
                    key={plan.id}
                    className="rounded-md border border-[#e6e8f1] bg-[#fafbff] p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <b className="text-xs">{plan.name}</b>
                      <Status>Active</Status>
                    </div>
                    <p className="mt-1 text-sm font-bold text-brand">
                      {formatPrice(plan.price)}
                      <span className="ml-1 text-[9px] font-semibold text-slate-400">
                        / {intervalLabel(plan.billing_interval)}
                      </span>
                    </p>
                    {plan.description && (
                      <p className="mt-1 text-[10px] text-slate-500">
                        {plan.description}
                      </p>
                    )}
                    {plan.features?.length > 0 && (
                      <ul className="mt-2 space-y-1 text-[10px] text-slate-600">
                        {plan.features.map((feature) => (
                          <li key={feature.label}>• {feature.label}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )
        })}
      </div>
    </Shell>
  )
}
