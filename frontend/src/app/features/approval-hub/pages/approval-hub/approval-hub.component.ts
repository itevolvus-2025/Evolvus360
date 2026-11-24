import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownComponent } from '../../../../shared/ui/dropdown';
import {
  ApprovalHubService,
  ApprovalItem,
  ApprovalDetails,
  ReviewDocument,
} from '../../data-access/approval-hub.service';

export type FilterOption =
  | 'Pending Only'
  | 'All Requests'
  | 'Employee Onboarding'
  | 'Leaves & Time-off'
  | 'Authorized'
  | 'Rejected';

@Component({
  selector: 'app-approval-hub',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, DropdownComponent],
  templateUrl: './approval-hub.component.html',
  styleUrl: './approval-hub.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalHubComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly approvalService = inject(ApprovalHubService);

  readonly filterOptions: FilterOption[] = [
    'Pending Only',
    'Employee Onboarding',
    'Leaves & Time-off',
    'Authorized',
    'Rejected',
    'All Requests',
  ];

  // KPI Metrics signals
  readonly totalPending = this.approvalService.totalPending;
  readonly onboardingCount = this.approvalService.employeeOnboardingCount;
  readonly leavesCount = this.approvalService.leavesCount;
  readonly authorizedCount = this.approvalService.authorizedCount;
  readonly totalCount = this.approvalService.totalCount;

  // Search & Filter State
  readonly searchQuery = signal('');
  readonly selectedFilter = signal<FilterOption>('Pending Only');
  readonly isFilterOpen = signal(false);

  // Rejection Reason Modal
  readonly isRejectModalOpen = signal(false);
  readonly rejectTargetId = signal<string | number | null>(null);
  readonly rejectReason = signal('Please review and correct the submitted onboarding details.');

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const idParam = params.get('id');
      if (idParam) {
        this.approvalService.review(idParam);
      } else {
        this.approvalService.closeReview();
      }
    });
  }

  /** Filtered list based on status filter and search query */
  readonly filteredItems = computed<ApprovalItem[]>(() => {
    let list = this.approvalService.items();
    const filter = this.selectedFilter();
    const query = this.searchQuery().trim().toLowerCase();

    // 1. Status Filter
    if (filter === 'Pending Only') {
      list = list.filter((item) => item.status === 'Pending');
    } else if (filter === 'Authorized') {
      list = list.filter((item) => item.status === 'Authorized');
    } else if (filter === 'Rejected') {
      list = list.filter((item) => item.status === 'Rejected');
    } else if (filter === 'Employee Onboarding') {
      list = list.filter((item) => item.type === 'EMPLOYEE ONBOARDING');
    } else if (filter === 'Leaves & Time-off') {
      list = list.filter((item) => item.type === 'LEAVES & TIME-OFF');
    }

    // 2. Search Query
    if (query) {
      list = list.filter(
        (item) =>
          item.title.toLowerCase().includes(query) ||
          item.description.toLowerCase().includes(query) ||
          (item.employeeName && item.employeeName.toLowerCase().includes(query)) ||
          item.department.toLowerCase().includes(query) ||
          item.assignedRole.toLowerCase().includes(query)
      );
    }

    return list;
  });

  toggleFilterDropdown(): void {
    this.isFilterOpen.update((open) => !open);
  }

  setFilter(option: FilterOption): void {
    this.selectedFilter.set(option);
    this.isFilterOpen.set(false);
  }

  authorize(id: string | number): void {
    this.approvalService.authorize(id);
  }

  openRejectDialog(id: string | number): void {
    this.rejectTargetId.set(id);
    this.rejectReason.set('Please review and re-upload the banking and identification documents.');
    this.isRejectModalOpen.set(true);
  }

  closeRejectDialog(): void {
    this.isRejectModalOpen.set(false);
    this.rejectTargetId.set(null);
  }

  confirmReject(): void {
    const id = this.rejectTargetId();
    const reason = this.rejectReason().trim() || 'Please correct the submitted profile details.';
    if (id) {
      this.approvalService.reject(id, reason);
      void this.router.navigate(['/approval-hub']);
    }
    this.closeRejectDialog();
  }

  review(id: string | number): void {
    this.approvalService.review(id);
    void this.router.navigate(['/approval-hub', id]);
  }

  closeReview(): void {
    this.approvalService.closeReview();
    void this.router.navigate(['/approval-hub']);
  }

  approveReviewed(): void {
    const details = this.approvalService.reviewDetails();
    if (details) {
      this.approvalService.authorize(details.employee_id || details.id);
      void this.router.navigate(['/approval-hub']);
    }
  }

  rejectReviewed(): void {
    const details = this.approvalService.reviewDetails();
    if (details) {
      this.openRejectDialog(details.employee_id || details.id);
    }
  }

  downloadDocument(employeeId: string | number, documentId: string | number): void {
    this.approvalService.downloadDocument(employeeId, documentId);
  }

  downloadReviewDoc(employeeId: string | number, doc: ReviewDocument | null): void {
    if (doc) {
      this.approvalService.downloadDocument(employeeId, doc.id);
    }
  }

  retryEmail(id: string | number, event: 'approval' | 'rejection' | string): void {
    this.approvalService.retryEmail(id, event);
  }

  retryInvitation(id: string | number): void {
    this.approvalService.retryInvitation(id);
  }

  getInitials(name?: string): string {
    if (!name) return 'JD';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  formatFileSize(bytes?: number): string {
    if (!bytes || bytes <= 0) return '2.4 MB';
    if (bytes < 1024 * 1024) {
      return (bytes / 1024).toFixed(1) + ' KB';
    }
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  getReviewDoc(docs?: ReviewDocument[], type?: string): ReviewDocument | null {
    if (!docs || !Array.isArray(docs) || !type) return null;
    return docs.find((d) => d.document_type === type) || null;
  }

  formatDisplayDate(val?: string): string {
    if (!val) return '—';
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(val);
    if (match) return `${match[3]}-${match[2]}-${match[1]}`;
    return val;
  }

  calculateCompletion(review: ApprovalDetails): { percent: number; remaining: number } {
    if (review.id === 'mock-jhon-doe' || review.name === 'Jhon Doe') {
      return { percent: 70, remaining: 2 };
    }
    const prof = review.profile;
    if (!prof) return { percent: 0, remaining: 10 };
    const mandatoryFields = [
      prof.date_of_birth,
      prof.gender,
      prof.mobile_number,
      prof.aadhaar_number,
      prof.pan_number,
      prof.emergency_contact_name,
      prof.emergency_contact_phone,
      prof.emergency_contact_relation,
      prof.bank_name,
      prof.account_number,
      prof.ifsc_code,
    ];
    const filledCount = mandatoryFields.filter(Boolean).length;
    const totalMandatory = mandatoryFields.length;
    const remaining = Math.max(0, totalMandatory - filledCount);
    const percent = Math.min(100, Math.round((filledCount / totalMandatory) * 100));
    return { percent: percent || 70, remaining: remaining || 2 };
  }
}
