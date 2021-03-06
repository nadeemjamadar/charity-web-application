from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail, EmailMessage
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, UpdateView

from charityapp.forms import RegisterForm, LoginForm, UpdateUserForm, ConfirmUserPasswordForm, ChangeUserPassword
from charityapp.models import Donation, Institution, Category


class LandingPageView(View):
    """Landing Page for charity app"""

    def get(self, request):
        """Simple counting for index view"""
        donation = Donation.objects.all()
        donation_quantity = sum([inst.quantity for inst in donation])
        institution = Institution.objects.count()

        # Pagination for foundations
        foundations_list = Institution.objects.filter(type="Fundacja").order_by("id")
        foundations_pagi = Paginator(foundations_list, 4)
        foundations_page = request.GET.get("page")
        foundations = foundations_pagi.get_page(foundations_page)

        # Pagination for organizations
        organizations_list = Institution.objects.filter(type="Organizacja pozarządowa").order_by("id")
        organizations_pagi = Paginator(organizations_list, 4)
        organizations_page = request.GET.get("page")
        organizations = organizations_pagi.get_page(organizations_page)

        # Pagination for local charity
        locals_list = Institution.objects.filter(type="Zbiórka lokalna").order_by("id")
        locals_pagi = Paginator(locals_list, 4)
        local_page = request.GET.get("page")
        locals_charity = locals_pagi.get_page(local_page)

        ctx = {
            "donation_quantity": donation_quantity,
            "institution": institution,
            "foundations": foundations,
            "organizations": organizations,
            "locals_charity": locals_charity,
        }
        return render(request, "pages/index.html", ctx)


class AddDonationView(LoginRequiredMixin, View):
    """View managing donations"""
    login_url = 'login'

    def get(self, request):
        categories = Category.objects.all()
        institutions = Institution.objects.all()
        ctx = {
            "categories": categories,
            "institutions": institutions
        }
        return render(request, "forms/form.html", ctx)

    def post(self, request):
        quantity = request.POST.get("bags")
        categories = request.POST.getlist("category")
        institution = request.POST.get("organization")
        address = request.POST.get("address")
        phone_number = request.POST.get("phone")
        city = request.POST.get("city")
        zip_code = request.POST.get("postcode")
        pick_up_date = request.POST.get("data")
        pick_up_time = request.POST.get("time")
        pick_up_comment = request.POST.get("more_info")
        user = request.user
        institution_instance = Institution.objects.get(id=institution)
        donation = Donation.objects.create(
            quantity=quantity,
            institution=institution_instance,
            address=address,
            phone_number=phone_number,
            city=city,
            zip_code=zip_code,
            pick_up_date=pick_up_date,
            pick_up_time=pick_up_time,
            pick_up_comment=pick_up_comment,
            user=user
        )
        for category_id in categories:
            donation.categories.add(Category.objects.get(id=category_id))
        if donation:
            return render(request, "forms/form-confirmation.html")
        else:
            return redirect("add-donation")


class DonationConfirmationView(View):
    """View showing confirmation of adding a donation"""

    def get(self, request):
        return render(request, "forms/form-confirmation.html")


class LoginView(View):
    """View to login user"""

    def get(self, request):
        form = LoginForm()
        return render(request, "forms/login.html", {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("landing-page")
            else:
                return redirect("register")
        else:
            return render(request, "forms/login.html", {"form": form})


class ConfirmUserPasswordView(View):
    """View for user password confirmation before going to change user data"""

    def get(self, request):
        form = ConfirmUserPasswordForm(user=request.user)
        return render(request, "forms/user-confirm-password.html", {"form": form})

    def post(self, request):
        form = ConfirmUserPasswordForm(request.POST, user=request.user)
        if form.is_valid():
            return redirect('update')
        else:
            return render(request, "forms/user-confirm-password.html", {"form": form})


class UpdateUserView(View):
    """View showing forms to change user data and also change password"""

    def get(self, request):
        user = request.user
        form1 = UpdateUserForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        })
        form2 = ChangeUserPassword(user=request.user)
        ctx = {"form1": form1, "form2": form2}
        return render(request, "forms/user-settings.html", ctx)

    def post(self, request):
        form1 = UpdateUserForm(request.POST)
        form2 = ChangeUserPassword(request.POST, user=request.user)
        ctx = {"form1": form1, "form2": form2}
        user = request.user

        # POST data from form nr 1
        if 'user-data' in request.POST:
            if form1.is_valid():
                first_name = form1.cleaned_data['first_name']
                last_name = form1.cleaned_data['last_name']
                email = form1.cleaned_data['email']
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
            else:
                return render(request, "forms/user-settings.html", ctx)

        # POST data from form nr 2
        elif 'user-password' in request.POST:
            if form2.is_valid():
                new_password = form2.cleaned_data['password_new']
                user.set_password(new_password)
                user.save()
                return redirect("login")
            else:
                return render(request, "forms/user-settings.html", ctx)
        return redirect("landing-page")


class UserProfileView(View):
    """View showing user profile, name, email etc., and donation history"""

    def get(self, request):
        donations = Donation.objects.filter(user=request.user).order_by("is_taken")
        return render(request, "forms/user-profile.html", {"donations": donations})

    def post(self, request):
        donations = Donation.objects.filter(user=request.user).order_by("is_taken")
        donation_id = request.POST.get('donation_id')
        donation = Donation.objects.get(id=donation_id)
        donation.is_taken = True
        donation.save()
        return render(request, "forms/user-profile.html", {"donations": donations})


class LogoutView(View):
    """Logout user View"""

    def get(self, request):
        logout(request)
        return redirect("landing-page")


class RegisterView(View):
    """ View to register new user"""

    def get(self, request):
        form = RegisterForm()
        return render(request, "forms/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                username=email,
            )
            return redirect("login")
        else:
            return render(request, "forms/register.html", {"form": form})


class ContactFormView(View):
    def post(self, request):
        name = request.POST.get('name')
        surname = request.POST.get('surname')
        text = request.POST.get('message')
        admin_list = User.objects.filter(is_superuser=True)
        email_list = []
        for admin in admin_list:
            email_list.append(admin.email)
        if request.user:
            message = text + f' -->> od użytkownika {request.user.email}'
        else:
            message = text + name + surname
        email = EmailMessage(
            f'Charity App mail from {name} {surname}',
            message,
            to=email_list
        )
        email.send()
        return render(request, "forms/message-confirmation.html")
