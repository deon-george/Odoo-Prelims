import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../api'
import { apiErrorMessage } from '../auth/errors'
import { Button } from '../components'
import AuthLayout, { AuthAlert, AuthField } from './AuthLayout'

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, 'Email is required.')
    .email('Enter a valid email address.'),
})

export default function ForgotPassword() {
  const [serverError, setServerError] = useState('')
  const [sentMessage, setSentMessage] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  const submit = async (values) => {
    setServerError('')
    try {
      const { data } = await api.post('/auth/forgot-password', {
        email: values.email.trim(),
      })
      setSentMessage(data.message)
    } catch (error) {
      setServerError(
        apiErrorMessage(error, 'Unable to send the reset link. Please try again.'),
      )
    }
  }

  return (
    <AuthLayout
      title="Forgot Password"
      subtitle="We'll email you a secure, time-limited reset link"
    >
      <form onSubmit={handleSubmit(submit)} noValidate>
        {serverError && <AuthAlert>{serverError}</AuthAlert>}
        {sentMessage && <AuthAlert type="success">{sentMessage}</AuthAlert>}

        <AuthField label="Email" error={errors.email}>
          <input
            {...register('email')}
            className="field mt-2"
            placeholder="Enter your account email"
            autoComplete="email"
          />
        </AuthField>

        <Button
          type="submit"
          disabled={isSubmitting || Boolean(sentMessage)}
          className="mt-8 w-full justify-center"
        >
          {isSubmitting ? 'Sending…' : 'Send reset link'}
        </Button>

        <p className="mt-5 text-center text-[10px]">
          <Link to="/login" className="font-bold text-brand">
            Back to login
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
