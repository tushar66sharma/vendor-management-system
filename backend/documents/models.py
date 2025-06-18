from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.utils import timezone
import uuid
import os

User = get_user_model()

class DocumentType(models.Model):
    """Document type configuration"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # File restrictions
    allowed_extensions = models.JSONField(default=list)  # ['pdf', 'jpg', 'png']
    max_file_size_mb = models.PositiveIntegerField(default=5)
    
    # Validation requirements
    requires_expiry_date = models.BooleanField(default=False)
    requires_document_number = models.BooleanField(default=False)
    requires_issuing_authority = models.BooleanField(default=False)
    
    # Workflow settings
    auto_approve = models.BooleanField(default=False)
    requires_verification = models.BooleanField(default=True)
    verification_levels = models.PositiveIntegerField(default=1)  # Number of approval levels
    
    # Categories
    CATEGORY_CHOICES = [
        ('personal', 'Personal Document'),
        ('vehicle', 'Vehicle Document'),
        ('driver', 'Driver Document'),
        ('business', 'Business Document'),
        ('financial', 'Financial Document'),
        ('legal', 'Legal Document'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_types'
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'
        
    def __str__(self):
        return self.name

class Document(models.Model):
    """Central document storage and management"""
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ]
    
    ENTITY_TYPE_CHOICES = [
        ('user', 'User'),
        ('driver', 'Driver'),
        ('vehicle', 'Vehicle'),
        ('vendor', 'Vendor'),
    ]
    
    # Document identification
    document_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='documents')
    
    # File information
    file = models.FileField(upload_to='documents/%Y/%m/', validators=[
        FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])
    ])
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    file_hash = models.CharField(max_length=64, blank=True, null=True)  # SHA256 hash for integrity
    
    # Document details
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issuing_authority = models.CharField(max_length=200, blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    
    # Entity relationship (polymorphic association)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.PositiveIntegerField()
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    current_verification_level = models.PositiveIntegerField(default=0)
    
    # Additional metadata
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list)  # Searchable tags
    
    # Tracking information
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_modified_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='modified_documents')
    
    # Access control
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='documents')
    is_public = models.BooleanField(default=False)  # Visible to all vendor hierarchy
    restricted_users = models.ManyToManyField(User, blank=True, related_name='restricted_documents')
    
    class Meta:
        db_table = 'documents'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['vendor']),
            models.Index(fields=['expiry_date']),
        ]
        
    def __str__(self):
        return f"{self.document_type.name} - {self.original_filename}"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def save(self, *args, **kwargs):
        if self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)

class DocumentVerification(models.Model):
    """Document verification workflow"""
    VERIFICATION_ACTION_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_correction', 'Needs Correction'),
        ('escalated', 'Escalated'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='verifications')
    verification_level = models.PositiveIntegerField()  # 1, 2, 3, etc.
    
    # Verifier information
    verified_by = models.ForeignKey(User, on_delete=models.CASCADE)
    verification_date = models.DateTimeField(auto_now_add=True)
    
    # Verification details
    action = models.CharField(max_length=20, choices=VERIFICATION_ACTION_CHOICES)
    comments = models.TextField(blank=True, null=True)
    issues_found = models.JSONField(default=list)  # List of issues
    
    # Correction requests
    correction_requested = models.BooleanField(default=False)
    correction_deadline = models.DateTimeField(blank=True, null=True)
    correction_instructions = models.TextField(blank=True, null=True)
    
    # Next steps
    next_verifier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_verifications')
    escalated_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_verifications')
    
    class Meta:
        db_table = 'document_verifications'
        verbose_name = 'Document Verification'
        verbose_name_plural = 'Document Verifications'
        ordering = ['-verification_date']
        unique_together = ['document', 'verification_level']
        
    def __str__(self):
        return f"{self.document.original_filename} - Level {self.verification_level} ({self.get_action_display()})"

class DocumentVersion(models.Model):
    """Document version control"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    
    # File information
    file = models.FileField(upload_to='document_versions/%Y/%m/')
    file_size = models.PositiveIntegerField()
    file_hash = models.CharField(max_length=64)
    
    # Version details
    change_summary = models.TextField()
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_current = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'document_versions'
        verbose_name = 'Document Version'
        verbose_name_plural = 'Document Versions'
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
        
    def __str__(self):
        return f"{self.document.original_filename} - v{self.version_number}"

class DocumentShareLog(models.Model):
    """Document sharing and access log"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='share_logs')
    
    # Sharing details
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_documents')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_documents')
    shared_at = models.DateTimeField(auto_now_add=True)
    
    # Access permissions
    can_view = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)
    can_share = models.BooleanField(default=False)
    
    # Expiry
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Access tracking
    first_accessed_at = models.DateTimeField(blank=True, null=True)
    last_accessed_at = models.DateTimeField(blank=True, null=True)
    access_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_shares')
    
    class Meta:
        db_table = 'document_share_logs'
        verbose_name = 'Document Share Log'
        verbose_name_plural = 'Document Share Logs'
        ordering = ['-shared_at']
        
    def __str__(self):
        return f"{self.document.original_filename} shared with {self.shared_with.get_full_name()}"

class DocumentComment(models.Model):
    """Comments on documents during verification"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comments')
    
    # Comment details
    comment = models.TextField()
    commenter = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Threading support
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Status
    is_internal = models.BooleanField(default=False)  # Internal comments not visible to document owner
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_comments')
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'document_comments'
        verbose_name = 'Document Comment'
        verbose_name_plural = 'Document Comments'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Comment on {self.document.original_filename} by {self.commenter.get_full_name()}"

class DocumentTemplate(models.Model):
    """Document templates for standardization"""
    name = models.CharField(max_length=200)
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='templates')
    
    # Template file
    template_file = models.FileField(upload_to='document_templates/')
    preview_image = models.ImageField(upload_to='template_previews/', blank=True, null=True)
    
    # Template details
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    required_fields = models.JSONField(default=list)  # Fields that must be filled
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_templates'
        verbose_name = 'Document Template'
        verbose_name_plural = 'Document Templates'
        
    def __str__(self):
        return f"{self.name} ({self.document_type.name})"

class DocumentNotification(models.Model):
    """Notifications related to documents"""
    NOTIFICATION_TYPE_CHOICES = [
        ('expiry_reminder', 'Expiry Reminder'),
        ('verification_required', 'Verification Required'),
        ('verification_completed', 'Verification Completed'),
        ('document_rejected', 'Document Rejected'),
        ('correction_required', 'Correction Required'),
        ('document_shared', 'Document Shared'),
        ('new_upload', 'New Document Uploaded'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_notifications')
    
    # Notification details
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)  # Additional notification data
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_notifications'
        verbose_name = 'Document Notification'
        verbose_name_plural = 'Document Notifications'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.get_full_name()}"

class DocumentAuditLog(models.Model):
    """Comprehensive audit log for document activities"""
    ACTION_CHOICES = [
        ('upload', 'Document Uploaded'),
        ('view', 'Document Viewed'),
        ('download', 'Document Downloaded'),
        ('update', 'Document Updated'),
        ('delete', 'Document Deleted'),
        ('verify', 'Document Verified'),
        ('reject', 'Document Rejected'),
        ('share', 'Document Shared'),
        ('revoke_share', 'Document Share Revoked'),
        ('comment', 'Comment Added'),
        ('status_change', 'Status Changed'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Action details
    description = models.TextField()
    old_values = models.JSONField(default=dict)  # Previous values
    new_values = models.JSONField(default=dict)  # New values
    
    # Request information
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_audit_logs'
        verbose_name = 'Document Audit Log'
        verbose_name_plural = 'Document Audit Logs'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.get_action_display()} on {self.document.original_filename}"
