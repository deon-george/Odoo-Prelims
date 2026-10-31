import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '../components'
import { useAuth } from '../auth/AuthContext'
import { apiErrorMessage } from '../auth/errors'
import { homeForRole } from '../auth/roles'
import AuthLayout, { AuthAlert, AuthField } from './AuthLayout'

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, 'Email is required.')
    .email('Enter a valid email address.'),
  password: z.string().min(1, 'Password is required.'),
})

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')
  const successMessage = location.state?.message || ''

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      email: location.state?.email || '',
      password: '',
    },
  })

  const submit = async (values) => {
    setServerError('')
    try {
      const user = await login(values.email.trim(), values.password)
      const requestedPath = location.state?.from?.pathname
      navigate(requestedPath || homeForRole(user.role), { replace: true })
    } catch (error) {
      setServerError(
        apiErrorMessage(error, 'Unable to sign in. Please try again.'),
      )
    }
  }

  return (
    <AuthLayout title="Welcome Back" subtitle="Sign in to your account">
      <form onSubmit={handleSubmit(submit)} noValidate>
        {successMessage && <AuthAlert type="success">{successMessage}</AuthAlert>}
        {serverError && <AuthAlert>{serverError}</AuthAlert>}

        <AuthField label="Email" error={errors.email}>
          <input
            {...register('email')}
            className="field mt-2"
            placeholder="Enter your email"
            autoComplete="email"
          />
        </AuthField>

        <div className="mt-3">
          <AuthField label="Password" error={errors.password}>
            <input
              {...register('password')}
              className="field mt-2"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
            />
          </AuthField>
        </div>

        <Link
          to="/forgot-password"
          className="float-right mt-2 text-[10px] font-semibold text-brand"
        >
          Forgot password?
        </Link>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="mt-8 w-full justify-center"
        >
          {isSubmitting ? 'Signing in…' : 'Login'}
        </Button>

        <p className="mt-5 text-center text-[10px]">
          Don't have an account?{' '}
          <Link to="/register" className="font-bold text-brand">
            Register
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
