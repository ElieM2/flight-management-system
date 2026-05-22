from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


AUTH_INPUT_CLASS = 'auth-input'
DASHBOARD_INPUT_CLASS = 'form-control'


def apply_widget_attrs(field, css_class, placeholder=None):
    existing_class = field.widget.attrs.get('class', '').strip()
    combined_class = f'{existing_class} {css_class}'.strip() if existing_class else css_class

    field.widget.attrs.update({
        'class': combined_class
    })

    if placeholder:
        field.widget.attrs.update({
            'placeholder': placeholder
        })


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        apply_widget_attrs(self.fields['username'], AUTH_INPUT_CLASS, 'Username')
        apply_widget_attrs(self.fields['email'], AUTH_INPUT_CLASS, 'Email address')
        apply_widget_attrs(self.fields['password1'], AUTH_INPUT_CLASS, 'Password')
        apply_widget_attrs(self.fields['password2'], AUTH_INPUT_CLASS, 'Confirm password')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()

        if commit:
            user.save()

        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Password'
        })
    )


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        apply_widget_attrs(self.fields['username'], DASHBOARD_INPUT_CLASS, 'Username')
        apply_widget_attrs(self.fields['email'], DASHBOARD_INPUT_CLASS, 'Email address')
        apply_widget_attrs(self.fields['first_name'], DASHBOARD_INPUT_CLASS, 'First name')
        apply_widget_attrs(self.fields['last_name'], DASHBOARD_INPUT_CLASS, 'Last name')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError('This email is already used by another account.')

        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'company', 'avatar']
        widgets = {
            'phone': forms.TextInput(),
            'company': forms.TextInput(),
            'avatar': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        apply_widget_attrs(self.fields['phone'], DASHBOARD_INPUT_CLASS, 'Phone number')
        apply_widget_attrs(self.fields['company'], DASHBOARD_INPUT_CLASS, 'Company / Organization')
        apply_widget_attrs(self.fields['avatar'], DASHBOARD_INPUT_CLASS)