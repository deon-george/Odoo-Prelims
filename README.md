# Subscription Management System

A responsive React + Vite frontend for a subscription-management system, built from the supplied UI reference images.

## Stack

- React 18 and Vite
- Tailwind CSS
- React Router
- Lucide React
- Recharts
- TanStack Query and Axios
- React Hook Form and Zod

## Getting started

```bash
npm install
npm run dev
```

Create a production bundle with:

```bash
npm run build
```

## Routes

| Route | Screen |
| --- | --- |
| `/login` | Sign-in page |
| `/` | Admin dashboard |
| `/staff` | Staff dashboard |
| `/products` | Product management |
| `/subscriptions` | Subscription list |
| `/quotations/new` | Create quotation |
| `/invoices` | Invoice list |
| `/invoices/:id` | Invoice details |
| `/portal` | Customer dashboard |
| `/portal/invoices` | Customer invoices |

Sidebar links provide navigation among the implemented views. Placeholder pages are also available for the remaining management sections.

## FastAPI integration

The Axios client is in `src/api.js`. It uses `http://localhost:8000/api` by default and can be configured with a Vite environment variable:

```bash
VITE_API_URL=http://localhost:8000/api
```

Current products and subscriptions request `/products` and `/subscriptions` through TanStack Query. While the backend is unavailable, the app displays local fallback data so that the UI remains usable during frontend development.

## Project structure

```text
src/
├── App.jsx          # Pages and route configuration
├── api.js           # Axios client and request helper
├── components.jsx   # Shared shell, cards, tables, controls
├── data.js          # Development fallback data
├── main.jsx         # Application bootstrap and Query provider
└── styles.css       # Tailwind directives and component styles
```
