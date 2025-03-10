from django.urls import path

from . import views
app_name= 'savings'

urlpatterns = [
	path('home/', views.savings, name="savings"),
	path('dashboard/', views.dashboard, name="dashboard"),
	path('transactions/', views.transactions, name="transactions"),
	path('withdrawal/', views.withdrawal, name="withdrawal"),
	path('plans/', views.plans, name="plans"),
	path('successful/', views.savings_success, name="success_page"),
	path('register-for-plan/daily_savings/', views.daily_savings, name="daily_savings"),
	path('register-for-plan/daily_contribution/', views.daily_contribution, name="daily_con"),
	path('deposit/daily_contribution/<int:plan_id>/', views.con_deposit_view, name="con_deposit"),
	path('verify_card_payment/', views.verify_card_payment, name='verify_card_payment'),
	path('card_payment/', views.card_pay, name='card_payment'),
	path('deposit/daily_savings/<int:plan_id>/', views.savings_deposit_view, name="savings_deposit"),
	path('api/deposit-calendar-data/savings/', views.savings_deposit_calendar_data, name='sav_deposit_calendar_data'),
	path('api/deposit-calendar-data/contribution/', views.con_deposit_calendar_data, name='con_deposit_calendar_data'),
	path('api/verify_transaction/deposit/', views.verify_transaction, name="verify_transaction"),
	path('api/con_verify_transaction/deposit/', views.con_verify_transaction, name="con_verify_transaction"),
	path('savings/dashboard/notifications/', views.notifications, name='notifications'),
] 