import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../api'
import { apiErrorMessage } from '../auth/errors'
import { Button } from '../components'
import AuthLayout, { AuthAlert, AuthField } from './AuthLayout'

const SPECIAL_CHARACTERS = /[!@#$%^&*()_+\-=\[\]{}|;:'",.<>/?~`\\]/

const schema = z
  .object({
    new_password: z
      .string()
      .min(9, 'Password must be more than 8 characters long.')
      .max(128, 'Password must be at most 128 characters long.')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter.')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter.')
      .regex(
        SPECIAL_CHARACTERS,
        'Password must contain at least one special character.',
      ),
    confirm_password: z.string().min(1, 'Please confirm your new password.'),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: 'Passwords do not match.',
    path: ['confirm_password'],
  })

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  const submit = async (values) => {
    setServerError('')
    try {
      const { data } = await api.post('/auth/reset-password', {
        token,
        new_password: values.new_password,
      })
      navigate('/login', {
        replace: true,
        state: { message: data.message },
      })
    } catch (error) {
      setServerError(
        apiErrorMessage(error, 'Unable to reset your password. Please try again.'),
      )
    }
  }

  return (
    <AuthLayout
      title="Reset Password"
      subtitle="Choose a new password for your account"
    >
      {!token ? (
        <>
          <AuthAlert>
            This reset link is missing its token. Please request a new link.
          </AuthAlert>
          <p className="text-center text-[10px]">
            <Link to="/forgot-password" className="font-bold text-brand">
              Request a new reset link
            </Link>
          </p>
        </>
      ) : (
        <form onSubmit={handleSubmit(submit)} noValidate>
          {serverError && <AuthAlert>{serverError}</AuthAlert>}

          <AuthField label="New Password" error={errors.new_password}>
            <input
              {...register('new_password')}
              className="field mt-2"
              type="password"
              placeholder="More than 8 characters, mixed case, special"
              autoComplete="new-password"
            />
          </AuthField>

          <div className="mt-3">
            <AuthField label="Confirm New Password" error={errors.confirm_password}>
              <input
                {...register('confirm_password')}
                className="field mt-2"
                type="password"
                placeholder="Re-enter your new password"
                autoComplete="new-password"
              />
            </AuthField>
          </div>

          <Button
            type="submit"
            disabled={isSubmitting}
            className="mt-8 w-full justify-center"
          >
            {isSubmitting ? 'Resetting…' : 'Reset password'}
          </Button>

          <p className="mt-5 text-center text-[10px]">
            <Link to="/login" className="font-bold text-brand">
              Back to login
            </Link>
          </p>
        </form>
      )}
    </AuthLayout>
  )
}
