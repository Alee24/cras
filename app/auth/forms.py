from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange
from app.models.auth import User
from app.models.organization import Organization


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Keep me logged in")
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    # Personal Info
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Work Email Address", validators=[DataRequired(), Email(), Length(max=150)])
    phone_number = StringField("Phone Number", validators=[DataRequired(), Length(min=9, max=20)])
    
    # Organization Info
    organization_name = StringField("Organization / Company Name", validators=[DataRequired(), Length(min=2, max=180)])
    business_registration_number = StringField("Business Registration / Certificate No.", validators=[DataRequired(), Length(min=3, max=50)])
    kra_pin = StringField("KRA PIN", validators=[DataRequired(), Length(min=9, max=20)])
    industry_sector = SelectField("Industry Sector", choices=[
        ("Services", "Professional & Commercial Services"),
        ("Financial Services", "Financial Services & Fintech"),
        ("Information Technology", "Information Technology & Software"),
        ("Healthcare & Pharmaceuticals", "Healthcare & Pharmaceuticals"),
        ("Retail & Wholesale", "Retail, Wholesale & FMCG"),
        ("Manufacturing & Industrial", "Manufacturing & Industrial"),
        ("Agriculture & Agribusiness", "Agriculture & Agribusiness"),
        ("Hospitality & Tourism", "Hospitality & Tourism"),
        ("Education & Training", "Education & Training"),
        ("Transport & Logistics", "Transport & Logistics"),
        ("Construction & Real Estate", "Construction & Real Estate"),
        ("Other", "Other Sector"),
    ], default="Services")
    business_type = SelectField("Entity Type", choices=[
        ("Private Limited Company", "Private Limited Company (Ltd)"),
        ("Public Limited Company", "Public Limited Company (PLC)"),
        ("Partnership", "Partnership / LLP"),
        ("Sole Proprietorship", "Sole Proprietorship / Business Name"),
        ("Non-Governmental Organization", "Non-Governmental Organization (NGO/Trust)"),
    ], default="Private Limited Company")
    organization_size = SelectField("Company Size", choices=[
        ("Micro (1-9)", "Micro (1 - 9 employees)"),
        ("Small (10-49)", "Small (10 - 49 employees)"),
        ("Medium (50-249)", "Medium (50 - 249 employees)"),
        ("Large (250+)", "Large (250+ employees)"),
    ], default="Small (10-49)")
    employee_count = IntegerField("Total Number of Employees", default=15, validators=[DataRequired(), NumberRange(min=1, max=10000)])
    county = SelectField("County of Principal Business", choices=[
        ("Nairobi", "Nairobi"),
        ("Mombasa", "Mombasa"),
        ("Kisumu", "Kisumu"),
        ("Nakuru", "Nakuru"),
        ("Kiambu", "Kiambu"),
        ("Machakos", "Machakos"),
        ("Uasin Gishu", "Uasin Gishu (Eldoret)"),
        ("Kajiado", "Kajiado"),
        ("Kilifi", "Kilifi"),
        ("Nyeri", "Nyeri"),
        ("Meru", "Meru"),
        ("Kakamega", "Kakamega"),
        ("Other", "Other County"),
    ], default="Nairobi")

    # Security
    password = PasswordField("Password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(),
        EqualTo("password", message="Passwords must match.")
    ])
    terms_agreed = BooleanField("I acknowledge that CRAS provides compliance intelligence and decision support, not legal certification.", validators=[DataRequired()])
    submit = SubmitField("Create SME Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email address already exists. Please log in.")

    def validate_business_registration_number(self, field):
        if Organization.query.filter_by(business_registration_number=field.data.strip().upper()).first():
            raise ValidationError("An organization with this registration number is already registered.")

    def validate_kra_pin(self, field):
        if Organization.query.filter_by(kra_pin=field.data.strip().upper()).first():
            raise ValidationError("An organization with this KRA PIN is already registered.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField("Confirm New Password", validators=[
        DataRequired(),
        EqualTo("new_password", message="Passwords must match.")
    ])
    submit = SubmitField("Update Password")


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    phone_number = StringField("Phone Number", validators=[DataRequired(), Length(min=9, max=20)])
    submit = SubmitField("Save Profile Changes")

