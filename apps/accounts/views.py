from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, ProfileUpdateForm, RegisterForm, UserUpdateForm
from .models import Profile


def get_safe_redirect_url(request, default_url_name):
    next_url = request.POST.get('next') or request.GET.get('next')

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return default_url_name


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    next_value = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect(get_safe_redirect_url(request, 'dashboard:dashboard'))
    else:
        form = RegisterForm()

    context = {
        'form': form,
        'next': next_value,
    }
    return render(request, 'accounts/register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    next_value = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'You are now logged in.')
            return redirect(get_safe_redirect_url(request, 'dashboard:dashboard'))
    else:
        form = LoginForm(request)

    context = {
        'form': form,
        'next': next_value,
    }
    return render(request, 'accounts/login.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('dashboard:home')


@login_required
def profile_view(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    context = {
        'user_obj': request.user,
        'profile_obj': profile_obj,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile_obj
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile_obj)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_obj': request.user,
        'profile_obj': profile_obj,
    }
    return render(request, 'accounts/edit_profile.html', context)