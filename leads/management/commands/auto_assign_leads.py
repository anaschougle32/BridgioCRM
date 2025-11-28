"""
Management command to auto-assign leads daily based on quotas
Run this daily via cron job or scheduled task
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from leads.models import Lead, DailyAssignmentQuota
from accounts.models import User


class Command(BaseCommand):
    help = 'Auto-assign leads to employees based on daily quotas'

    def handle(self, *args, **options):
        self.stdout.write('Starting daily lead assignment...')
        
        # Get all active quotas
        quotas = DailyAssignmentQuota.objects.filter(is_active=True)
        
        total_assigned = 0
        
        for quota in quotas:
            # Get unassigned leads for this project
            unassigned_leads = Lead.objects.filter(
                project=quota.project,
                assigned_to__isnull=True,
                is_archived=False
            ).order_by('created_at')
            
            # Assign leads up to daily quota
            leads_to_assign = list(unassigned_leads[:quota.daily_quota])
            
            for lead in leads_to_assign:
                lead.assigned_to = quota.employee
                lead.assigned_by = quota.created_by
                lead.assigned_at = timezone.now()
                lead.save()
                total_assigned += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Assigned lead #{lead.id} ({lead.name}) to {quota.employee.username}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully assigned {total_assigned} lead(s) to employees.')
        )

