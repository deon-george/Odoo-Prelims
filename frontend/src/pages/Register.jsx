import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '../components'
import { useAuth } from '../auth/AuthContext'
import { apiErrorMessage } from '../auth/errors'
import AuthLayout, { AuthAlert, AuthField } from './AuthLayout'

// Mirrors backend/app/core/password_policy.py so users get instant feedback.
const SPECIAL_CHARACTERS = /[!@#$%^&*()_+\-=\[\]{}|;:'",.<>/?~`\\]/

const schema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, 'Full name must be at least 2 characters.')
      .max(150, 'Full name must be at most 150 characters.'),
    email: z
      .string()
      .trim()
      .min(1, 'Email is required.')
      .email('Enter a valid email address.'),
    password: z
      .string()
      .min(9, 'Password must be more than 8 characters long.')
      .max(128, 'Password must be at most 128 characters long.')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter.')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter.')
      .regex(
        SPECIAL_CHARACTERS,
        'Password must contain at least one special character.',
      ),
    confirm_password: z.string().min(1, 'Please confirm your password.'),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: 'Passwords do not match.',
    path: ['confirm_password'],
  })

export default function Register() {
  const { register: registerAccount } = useAuth()
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
      await registerAccount({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        password: values.password,
      })
      navigate('/login', {
        replace: true,
        state: {
          message: 'Your customer account was created. Please sign in.',
          email: values.email.trim(),
        },
      })
    } catch (error) {
      setServerError(
        apiErrorMessage(error, 'Unable to create your account. Please try again.'),
      )
    }
  }

  return (
    <AuthLayout
      title="Create Account"
      subtitle="Register as a customer to manage your subscriptions"
    >
      <form onSubmit={handleSubmit(submit)} noValidate>
        {serverError && <AuthAlert>{serverError}</AuthAlert>}

        <AuthField label="Full Name" error={errors.full_name}>
          <input
            {...register('full_name')}
            className="field mt-2"
            placeholder="Enter your full name"
            autoComplete="name"
          />
        </AuthField>

        <div className="mt-3">
          <AuthField label="Email" error={errors.email}>
            <input
              {...register('email')}
              className="field mt-2"
              placeholder="Enter your email"
              autoComplete="email"
            />
          </AuthField>
        </div>

        <div className="mt-3">
          <AuthField label="Password" error={errors.password}>
            <input
              {...register('password')}
              className="field mt-2"
              type="password"
              placeholder="More than 8 characters, mixed case, special"
              autoComplete="new-password"
            />
          </AuthField>
        </div>

        <div className="mt-3">
          <AuthField label="Confirm Password" error={errors.confirm_password}>
            <input
              {...register('confirm_password')}
              className="field mt-2"
              type="password"
              placeholder="Re-enter your password"
              autoComplete="new-password"
            />
          </AuthField>
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="mt-8 w-full justify-center"
        >
          {isSubmitting ? 'Creating account…' : 'Register'}
        </Button>

        <p className="mt-5 text-center text-[10px]">
          Already have an account?{' '}
          <Link to="/login" className="font-bold text-brand">
            Login
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
