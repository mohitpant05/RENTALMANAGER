def welcome_email(full_name: str) -> str:
    return f"""Hi {full_name},

Welcome to RentManager! Your account has been created successfully.

You can now browse and book available resources. If you have any questions, feel free to reach out to our support team.

Best regards,
The RentManager Team"""


def booking_confirmation_email(
    full_name: str, resource_name: str, start: str, end: str, total: str,
    booking_id: str | None = None, booking_group_id: str | None = None,
) -> str:
    ref_label = "Bundle ID" if booking_group_id else "Booking ID"
    ref_value = booking_group_id or booking_id or ""
    return f"""Hi {full_name},

Your booking has been confirmed!

{ref_label}: {ref_value}
Resource: {resource_name}
Start:    {start}
End:      {end}
Total:    {total}

Thank you for choosing RentManager.

Best regards,
The RentManager Team"""


def booking_status_change_email(full_name: str, resource_name: str, status: str) -> str:
    return f"""Hi {full_name},

Your booking for "{resource_name}" has been updated to: {status}.

If you have any questions, please contact our support team.

Best regards,
The RentManager Team"""


def password_reset_email(full_name: str, reset_url: str) -> str:
    return f"""Hi {full_name},

We received a request to reset your password.

Click the link below to set a new password:
{reset_url}

This link expires in 1 hour. If you did not request this, you can safely ignore this email.

Best regards,
The RentManager Team"""


def email_change_otp_email(full_name: str, otp: str) -> str:
    return f"""Hi {full_name},

You requested to change your email address. Use the code below to verify:

{otp}

This code expires in 10 minutes. If you did not request this, you can safely ignore this email.

Best regards,
The RentManager Team"""


def invite_email(full_name: str, invite_url: str) -> str:
    return f"""Hi {full_name},

You have been invited to join RentManager as a staff member.

Please click the link below to accept the invitation and set your password:
{invite_url}

This invitation will expire in 72 hours.

Best regards,
The RentManager Team"""
