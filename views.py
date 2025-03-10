from .models import *
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django.contrib import messages
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from datetime import date, timedelta, datetime
from django.urls import reverse
import json
import requests
from django.conf import settings


def savings(request):
    user = request.user
    if user.is_authenticated:
        return redirect('savings:dashboard')
    return render(request, 'savings/savings.html')

@login_required(login_url='accounts:login')
def dashboard(request):
    client = request.user.client  
    model_client = Client.objects.get(user=request.user)  
    total_balance = model_client.calculate_total_balance()
    cardpayment = CardPayment.objects.filter(user=client).first()
    savings_plans = DailySavings.objects.filter(user=client)
    contribution = DailyContribution.objects.filter(user=client)
    has_savings_plan = savings_plans.exists()
    has_contribution_plan = contribution.exists()

    context = {
        'savings': savings_plans,
        'cardpayment': cardpayment,
        "contribution": contribution,
        "total_balance": total_balance,
        'has_savings_plan': has_savings_plan,
        'has_contribution_plan': has_contribution_plan,
    }
    return render(request, 'savings/savings-dashboard.html', context)



@login_required(login_url='accounts:login')
def savings_deposit_view(request, plan_id):
    client = request.user.client
    savings_plan = get_object_or_404(DailySavings, id=plan_id, user=client)

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            deposit_days = int(request.POST.get('deposit_days', 1))  
            print(f"Deposit Days: {deposit_days}")


            # Validate amount
            if amount < savings_plan.daily_savings_goal * deposit_days:
                return JsonResponse({
                    'success': False,
                    'message': f'Amount must be at least ₦{savings_plan.daily_savings_goal * deposit_days}.'
                }, status=400)
                print(f"Deposit Days: {deposit_days}")

            # Determine the next available deposit date
            current_year = timezone.now().year
            first_jan = date(current_year, 1, 1)
            next_deposit_date = first_jan

            if DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=first_jan).exists():
                unchecked_days = [
                    first_jan + timedelta(days=i)
                    for i in range(1, 365)
                ]
                for day in unchecked_days:
                    if not DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=day).exists():
                        next_deposit_date = day
                        break

            # Create deposits and update the savings plan
            with transaction.atomic():
                for i in range(deposit_days):
                    deposit_date = next_deposit_date + timedelta(days=i)
                    if not DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=deposit_date).exists():
                        DailySavingsDeposit.objects.create(
                            daily_savings=savings_plan,
                            deposit_date=deposit_date,
                            amount=amount / deposit_days,
                        )

                savings_plan.total += amount
                savings_plan.save()

            messages.success(request, 'Deposit request submitted successfully! It will be confirmed shortly.')
            return redirect('savings:dashboard')

        except ValueError as e:
            # Handle invalid input
            return JsonResponse({
                'success': False,
                'message': 'Invalid input provided. Please try again.'
            }, status=400)

    return render(request, 'savings/savings-deposit.html', {'savings': savings_plan})

@login_required(login_url='accounts:login')
def con_deposit_view(request, plan_id):
    client = request.user.client
    savings_plan = get_object_or_404(DailyContribution, id=plan_id, user=client)
    cardpayment = CardPayment.objects.filter(user=client).first()

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            deposit_days = int(request.POST.get('deposit_days', 1))  
            print(f"Deposit Days: {deposit_days}")


            # Validate amount
            if amount < savings_plan.daily_savings_goal * deposit_days:
                return JsonResponse({
                    'success': False,
                    'message': f'Amount must be at least ₦{savings_plan.daily_savings_goal * deposit_days}.'
                }, status=400)
                print(f"Deposit Days: {deposit_days}")

            # Determine the next available deposit date
            current_year = timezone.now().year
            first_jan = date(current_year, 1, 1) 
            next_deposit_date = first_jan

            if DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=first_jan).exists():
                unchecked_days = [
                    first_jan + timedelta(days=i)
                    for i in range(1, 365)
                ]
                for day in unchecked_days:
                    if not DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=day).exists():
                        next_deposit_date = day
                        break

            # Create deposits and update the savings plan
            with transaction.atomic():
                for i in range(deposit_days):
                    deposit_date = next_deposit_date + timedelta(days=i)
                    if not DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=deposit_date).exists():
                        DailyContributionDeposit.objects.create(
                            daily_contribution=savings_plan,
                            deposit_date=deposit_date,
                            amount=amount / deposit_days,
                        )

                savings_plan.total += amount
                savings_plan.save()

            messages.success(request, 'Deposit request submitted successfully! It will be confirmed shortly.')
            return redirect('savings:dashboard')

        except ValueError as e:
            # Handle invalid input
            return JsonResponse({
                'success': False,
                'message': 'Invalid input provided. Please try again.'
            }, status=400)

    return render(request, 'savings/con-deposit.html', {'contribution': savings_plan, 'cardpayment': cardpayment,})




def card_pay(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('payment', 0))
            CardPayment.objects.update_or_create(
                user=request.user.client,
                defaults={'paid': True, 'amount': amount}
            )
            messages.success(request, 'Card payment successful!')
            return redirect('savings:dashboard')
        except Exception as e:
            messages.error(request, 'Error processing card payment. Please try again.')
            return redirect('savings:deposit_page')
          

 
def verify_card_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reference = data.get('reference')

            # Verify the transaction with Paystack API
            url = f"https://api.paystack.co/transaction/verify/{reference}"
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'  # Use your secret key
            }
            response = requests.get(url, headers=headers)
            result = response.json()

            if result.get('status') and result['data']['status'] == 'success':
                amount = Decimal(result['data']['amount'])

                # Update database to mark card payment as paid
                CardPayment.objects.update_or_create(
                    user=request.user.client,
                    defaults={'paid': True, 'amount': amount}
                )
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'failed', 'message': result.get('message', 'Payment verification failed.')})
        except IntegrityError as e:
            return JsonResponse({'status': 'failed', 'message': f'Database error: {str(e)}'})
        except Exception as e:
            return JsonResponse({'status': 'failed', 'message': f'Error: {str(e)}'})


@login_required(login_url='accounts:login')
@csrf_exempt
def savings_deposit_calendar_data(request):
    client = request.user.client
    savings_id = request.GET.get('id')
    deposits = DailySavingsDeposit.objects.filter(
        daily_savings__user=client,
        daily_savings_id=savings_id,
        status="approved"
    )
    deposit_dates = [deposit.deposit_date.isoformat() for deposit in deposits]  # Use ISO format for consistency
    return JsonResponse({'deposit_dates': deposit_dates})




@login_required(login_url='accounts:login')
@csrf_exempt
def con_deposit_calendar_data(request):
    client = request.user.client
    contribution_id = request.GET.get('id')  # Use request.GET instead of request.get
    if not contribution_id:
        return JsonResponse({'deposit_dates': []})  # Return empty if no contribution_id is provided

    deposits = DailyContributionDeposit.objects.filter(
        daily_contribution__user=client,
        daily_contribution_id=contribution_id,
        status="approved"
    )
    deposit_dates = [deposit.deposit_date.isoformat() for deposit in deposits]  # Use ISO format for consistency
    return JsonResponse({'deposit_dates': deposit_dates})



# @login_required(login_url='accounts:login')
# def savings_deposit_view(request, plan_id):
#     client = request.user.client
#     savings = get_object_or_404(DailySavings, id=plan_id, user=client)

#     if request.method == 'POST':
#         deposit_amount = Decimal(request.POST.get('amount', 0))

#         if deposit_amount < savings.daily_savings_goal:
#             messages.error(request, f"Deposit amount must be at least {savings.daily_savings_goal}.")
#             return render(request, 'savings/savings-deposit.html', {'savings': savings})

    
#         savings.total += deposit_amount
#         savings.save()

#         DailySavingsDeposit.objects.create(daily_savings=savings, amount=deposit_amount)

#         messages.success(request, 'Deposit added successfully!')
#         return redirect('savings:dashboard')

#     return render(request, 'savings/savings-deposit.html', {'savings': savings}) 
 
@login_required
@csrf_exempt
def verify_transaction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reference = data.get('reference')
        amount = Decimal(data.get('amount', 0))
        deposit_days = int(data.get('deposit_days', 1))
        
        if not reference:
            return JsonResponse({'success': False, 'message': 'Transaction reference is required.'}, status=400)

        # Verify transaction with Paystack
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        }
        response = requests.get(url, headers=headers)
        result = response.json()

        if result.get('status') and result['data']['status'] == 'success':
            client = request.user.client
            savings_plan = get_object_or_404(DailySavings, user=client)
            if amount < savings_plan.daily_savings_goal * deposit_days:
                return JsonResponse({
                    'success': False,
                    'message': f'Amount must be at least ₦{savings_plan.daily_savings_goal * deposit_days}.'
                }, status=400)

            # Update savings plan and calendar
            current_year = timezone.now().year
            first_jan = date(current_year, 1, 1)

            next_deposit_date = first_jan
            if DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=first_jan).exists():
                unchecked_days = [
                    first_jan + timedelta(days=i)
                    for i in range(1, 365)
                ]
                for day in unchecked_days:
                    if not DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=day).exists():
                        next_deposit_date = day
                        break

            with transaction.atomic():
                for i in range(deposit_days):
                    deposit_date = next_deposit_date + timedelta(days=i)
                    if not DailySavingsDeposit.objects.filter(daily_savings=savings_plan, deposit_date=deposit_date).exists():
                        DailySavingsDeposit.objects.create(
                            daily_savings=savings_plan,
                            deposit_date=deposit_date,
                            amount=amount / deposit_days
                        )

                savings_plan.total += amount
                savings_plan.save()

            return JsonResponse({'success': True, 'message': 'Deposit successful!'})
        else:
            return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
  

@login_required
@csrf_exempt
def con_verify_transaction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reference = data.get('reference')
        amount = Decimal(data.get('amount', 0))  
        deposit_days = int(data.get('deposit_days', 1))
        
        if not reference:
            return JsonResponse({'success': False, 'message': 'Transaction reference is required.'}, status=400)

        # Verify transaction with Paystack
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        }
        response = requests.get(url, headers=headers)
        result = response.json()

        if result.get('status') and result['data']['status'] == 'success':
            client = request.user.client
            savings_plan = get_object_or_404(DailyContribution, user=client)
            if amount < savings_plan.daily_savings_goal * deposit_days:
                return JsonResponse({
                    'success': False,
                    'message': f'Amount must be at least ₦{savings_plan.daily_savings_goal * deposit_days}.'
                }, status=400)

            # Update savings plan and calendar
            current_year = timezone.now().year
            first_jan = date(current_year, 1, 1)

            next_deposit_date = first_jan
            if DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=first_jan).exists():
                unchecked_days = [
                    first_jan + timedelta(days=i)
                    for i in range(1, 365)
                ]
                for day in unchecked_days:
                    if not DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=day).exists():
                        next_deposit_date = day
                        break

            with transaction.atomic():
                for i in range(deposit_days):
                    deposit_date = next_deposit_date + timedelta(days=i)
                    if not DailyContributionDeposit.objects.filter(daily_contribution=savings_plan, deposit_date=deposit_date).exists():
                        DailyContributionDeposit.objects.create(
                            daily_contribution=savings_plan,
                            deposit_date=deposit_date,
                            amount=amount / deposit_days
                        )

                savings_plan.total += amount
                savings_plan.save()

            return JsonResponse({'success': True, 'message': 'Deposit successful!'})
        else:
            return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
  

@login_required(login_url='accounts:login')
def transactions(request):
    client = request.user.client
    sav_deposits = DailySavingsDeposit.objects.filter(daily_savings__user=client).order_by('-deposit_date') 
    con_deposits = DailyContributionDeposit.objects.filter(daily_contribution__user=client).order_by("-deposit_date")
    withdrawals = Withdrawal.objects.filter(user=client).order_by("-date")
    context = {'sav_deposits': sav_deposits, "con_deposits":con_deposits, 'withdrawals':withdrawals}
    return render(request, 'savings/savings-transactions.html', context)

@login_required(login_url='accounts:login')
def withdrawal(request):
    model_client = Client.objects.get(user=request.user)
    total_balance = model_client.calculate_total_balance()

    if request.method == "POST":
        bank = request.POST.get('bank')
        acc_no = request.POST.get('acc_no')
        plan = request.POST.get('plan')
        amount = Decimal(request.POST.get('amount', 0))

        if amount > total_balance:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient balance.'
            }, status=400)

        withdraw = Withdrawal(
            user=request.user.client,
            amount=amount,
            plan=plan,
            bank=bank,
            acc_no=acc_no,
            date=timezone.now()
        )
        withdraw.save()
        return JsonResponse({
            'success': True,
            'message': 'Withdrawal request submitted successfully!'
        })
    return render(request, 'savings/savings-withdrawal.html', { "total_balance": total_balance })


@login_required(login_url='accounts:login')
def plans(request):
    client = request.user.client
    saving = DailySavings.objects.filter(user=client)
    contribution = DailyContribution.objects.filter(user=client)
    context = {
        'savings':saving,
        'contribution':contribution,
    }
    return render(request, 'savings/savings-plans.html', context)

@login_required(login_url='accounts:login')
def savings_success(request):
    return render(request, 'savings/savings-success.html')


@login_required(login_url='accounts:login')
def daily_savings(request):
    if request.method == "POST":
        daily_savings_goal = request.POST.get('daily_savings_goal')
        package = request.POST.get('package')

        # Save the savings plan
        savings_plan = DailySavings(
            user=request.user.client,
            daily_savings_goal=daily_savings_goal,
            package=package,
            date_started=timezone.now()
        )
        savings_plan.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Savings plan created successfully!'
        })
    
    return render(request, 'savings/daily-savings.html')



@login_required(login_url='accounts:login')
def daily_contribution(request):
    if request.method == "POST":
        daily_savings_goal = request.POST.get('daily_savings_goal')
        package = request.POST.get('package')

        # Save the savings plan
        savings_plan = DailyContribution(
            user=request.user.client,
            daily_savings_goal=daily_savings_goal,
            package=package,
            date_started=timezone.now()
        )
        savings_plan.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Savings plan created successfully!'
        })
    
    return render(request, 'savings/daily-con.html')


@login_required(login_url='accounts:login')
def notifications(request):
    model = Notification.objects.filter(user=request.user.client).order_by('-date_added').last()
    return render(request, 'savings/notifications.html', {'notifications':model})