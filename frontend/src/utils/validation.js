export const passwordRequirements = [
  'At least 9 characters',
  'One uppercase letter',
  'One lowercase letter',
  'One special character',
]

export function validatePassword(value) {
  const errors = []
  if (value.length < 9) errors.push(passwordRequirements[0])
  if (!/[A-Z]/.test(value)) errors.push(passwordRequirements[1])
  if (!/[a-z]/.test(value)) errors.push(passwordRequirements[2])
  if (!/[^A-Za-z0-9]/.test(value)) errors.push(passwordRequirements[3])
  return errors
}

export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(' ')
  return detail || error?.message || fallback
}
