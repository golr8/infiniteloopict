from django.contrib import admin
from .models import *


class DailyContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_savings_goal', 'package')
    
class DailySavingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_savings_goal', 'package')

class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_id', 'calculated_total_balance')
    
    def calculated_total_balance(self, obj):
        return obj.calculate_total_balance()
    calculated_total_balance.short_description = 'Calculated Total Balance'
    
    # Custom method to display the user ID
    def user_id(self, obj):
        return obj.user.id  # Access the related user's ID
    user_id.short_description = 'User ID CH000'  # Label for the column in the admin
    
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_id', 'amount', 'plan', 'date')
    
    def user_id(self, obj):
        return obj.user.id  # Access the related user's ID
    user_id.short_description = 'User ID CH000'  # Label for the column in the admin
    
@admin.register(DailySavingsDeposit)
class DailySavingsDepositAdmin(admin.ModelAdmin):
    list_display = ('daily_savings', 'deposit_date', 'amount', 'deposit_days', 'status')
    actions = ['approve_deposits', 'reject_deposits']

    def approve_deposits(self, request, queryset):
        approved_count = 0
        for deposit in queryset.filter(status='pending'):
            deposit.status = 'approved'
            deposit.save()
            deposit.daily_savings.total += deposit.amount
            deposit.daily_savings.save()
            approved_count += 1
        self.message_user(request, f"{approved_count} deposits approved.")

    def reject_deposits(self, request, queryset):
        rejected_count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{rejected_count} deposits rejected.")

    approve_deposits.short_description = "Approve selected deposits"
    reject_deposits.short_description = "Reject selected deposits"

@admin.register(DailyContributionDeposit)
class DailyContributionDepositAdmin(admin.ModelAdmin):
    list_display = ('daily_contribution', 'deposit_date', 'amount', 'deposit_days', 'status')
    actions = ['approve_deposits', 'reject_deposits']

    def approve_deposits(self, request, queryset):
        approved_count = 0
        for deposit in queryset.filter(status='pending'):
            deposit.status = 'approved'
            deposit.save()
            deposit.daily_contribution.total += deposit.amount
            deposit.daily_contribution.save()
            approved_count += 1
        self.message_user(request, f"{approved_count} deposits approved.")

    def reject_deposits(self, request, queryset):
        rejected_count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{rejected_count} deposits rejected.")

    approve_deposits.short_description = "Approve selected deposits"
    reject_deposits.short_description = "Reject selected deposits"

class CardPaymentAdmin(admin.ModelAdmin):
    list_display = ( 'user','paid', 'amount', 'date_paid')

admin.site.register(DailyContribution, DailyContributionAdmin)
admin.site.register(DailySavings, DailySavingsAdmin)
admin.site.register(Client, ClientAdmin)  
admin.site.register(Withdrawal, WithdrawalAdmin)
admin.site.register(CardPayment, CardPaymentAdmin)
admin.site.register(Notification)
admin.site.register(PaystackTransaction)