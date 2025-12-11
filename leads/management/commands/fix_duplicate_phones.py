from django.core.management.base import BaseCommand
from leads.models import Lead
from django.db.models import Count


class Command(BaseCommand):
    help = 'Fix duplicate phone numbers by merging them'

    def handle(self, *args, **options):
        # Find all duplicate phone numbers
        duplicates = Lead.objects.values('phone').annotate(
            count=Count('phone')
        ).filter(count__gt=1, phone__isnull=False).exclude(phone='')
        
        total_duplicates = 0
        merged_count = 0
        
        for dup in duplicates:
            phone = dup['phone']
            if not phone:
                continue
                
            # Get all leads with this phone number
            leads_with_phone = Lead.objects.filter(phone=phone).order_by('id')
            total_duplicates += leads_with_phone.count() - 1
            
            # Keep the first one (oldest), merge data from others
            primary_lead = leads_with_phone.first()
            duplicate_leads = list(leads_with_phone[1:])
            
            self.stdout.write(f"Found {len(duplicate_leads)} duplicate(s) for phone: {phone}")
            
            for dup_lead in duplicate_leads:
                # Merge notes if both have notes
                if dup_lead.notes and primary_lead.notes:
                    primary_lead.notes = f"{primary_lead.notes}\n\n[Merged from duplicate lead #{dup_lead.id}]: {dup_lead.notes}"
                elif dup_lead.notes:
                    primary_lead.notes = dup_lead.notes
                
                # Update other fields if primary is missing them
                if not primary_lead.email and dup_lead.email:
                    primary_lead.email = dup_lead.email
                if not primary_lead.name and dup_lead.name:
                    primary_lead.name = dup_lead.name
                
                # Save primary lead
                primary_lead.save()
                
                # Delete the duplicate lead
                dup_lead.delete()
                merged_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Merged and deleted duplicate lead #{dup_lead.id}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nTotal duplicates found: {total_duplicates}"))
        self.stdout.write(self.style.SUCCESS(f"Total merged: {merged_count}"))
        self.stdout.write(self.style.SUCCESS("Duplicate phone numbers have been fixed!"))

