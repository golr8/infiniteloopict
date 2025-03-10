from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Q
from django.db.models.signals import post_save
from django.dispatch import receiver


User = get_user_model()


class Client(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    address = models.TextField(blank=True, null=True)
    total_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    def __str__(self):
        return str(self.user)

    def calculate_total_balance(self):
        # Calculate approved deposits for DailySavings
        daily_savings_total = DailySavingsDeposit.objects.filter(
            daily_savings__user=self,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate approved deposits for DailyContribution (if applicable)
        daily_contribution_total = DailyContributionDeposit.objects.filter(
            daily_contribution__user=self,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return daily_savings_total + daily_contribution_total
    
    def save(self, *args, **kwargs):
        if self.total_balance is None or self.total_balance == 0:
            self.total_balance = self.calculate_total_balance()
        super(Client, self).save(*args, **kwargs)




# Signal to create Client instance when a new User is created
@receiver(post_save, sender=User)
def create_client(sender, instance, created, **kwargs):
    if created:
        Client.objects.create(user=instance)


class Withdrawal(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.IntegerField()
    bank = models.CharField(max_length=200)
    acc_no = models.IntegerField()
    plan = models.CharField(max_length=250) 
    date = models.DateField(default=timezone.now)
    success = models.BooleanField(default=False)

    def __str__(self):
        return self.user.user.first_name


class DailySavings(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    daily_savings_goal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    package = models.CharField(max_length=150)
    total =  models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    date_started = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.user.first_name}'s Saving Plan"


class DailyContribution(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    package = models.CharField(max_length=200)
    daily_savings_goal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    date_started = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.user.user.first_name}'s Saving Plan"
 

class DailySavingsDeposit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    daily_savings = models.ForeignKey(DailySavings, on_delete=models.CASCADE)
    deposit_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_days = models.IntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Deposit on {self.deposit_date} ({self.get_status_display()}) for {self.daily_savings.user.user}"
    
class DailyContributionDeposit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    daily_contribution = models.ForeignKey(DailyContribution, on_delete=models.CASCADE)
    deposit_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_days = models.IntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Deposit on {self.deposit_date} for {self.daily_contribution.user.user}"
    
class CardPayment(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10 ,decimal_places=2)
    date_paid = models.DateField(default=timezone.now)
    paid = models.BooleanField(default=False)

class Notification(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    content = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user
    

class PaystackTransaction(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('success', 'Success')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.reference}"
