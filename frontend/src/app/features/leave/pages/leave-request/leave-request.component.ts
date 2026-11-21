import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { AuthService } from '../../../../core/services/auth.service';

export interface MyLeaveRequest {
  id: string;
  leaveType: string;
  fromDate: string;
  toDate: string;
  days: number;
  reason: string;
  status: 'Pending' | 'Approved' | 'Rejected';
  appliedOn: string;
  approver: string;
}

@Component({
  selector: 'app-leave-request',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './leave-request.component.html',
  styleUrl: './leave-request.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LeaveRequestComponent {
  private readonly notification = inject(NotificationService);
  readonly auth = inject(AuthService);

  readonly leaveType = signal('Annual Leave');
  readonly fromDate = signal('2026-12-01');
  readonly toDate = signal('2026-12-04');
  readonly daysCount = signal(4);
  readonly reason = signal('');
  readonly isSubmitting = signal(false);

  readonly showApplyModal = signal(false);

  readonly myRequests = signal<MyLeaveRequest[]>([
    {
      id: 'LR-1082',
      leaveType: 'Annual Leave',
      fromDate: '01 Dec 2026',
      toDate: '04 Dec 2026',
      days: 4,
      reason: 'Family vacation and personal travel',
      status: 'Pending',
      appliedOn: '18 Nov 2026',
      approver: 'HR Manager',
    },
    {
      id: 'LR-1049',
      leaveType: 'Sick Leave',
      fromDate: '10 Oct 2026',
      toDate: '11 Oct 2026',
      days: 2,
      reason: 'Medical recovery & doctor consultation',
      status: 'Approved',
      appliedOn: '09 Oct 2026',
      approver: 'Super Admin',
    },
    {
      id: 'LR-1011',
      leaveType: 'Casual Leave',
      fromDate: '15 Aug 2026',
      toDate: '15 Aug 2026',
      days: 1,
      reason: 'Personal urgent errand',
      status: 'Approved',
      appliedOn: '12 Aug 2026',
      approver: 'Reporting Manager',
    },
  ]);

  readonly leaveBalances = [
    { type: 'Annual Leave', total: 18, used: 4, remaining: 14, icon: 'calendar', color: '#2563EB' },
    { type: 'Sick Leave', total: 10, used: 2, remaining: 8, icon: 'check-circle', color: '#10B981' },
    { type: 'Casual Leave', total: 7, used: 1, remaining: 6, icon: 'clock', color: '#F59E0B' },
  ];

  openApplyModal(): void {
    this.showApplyModal.set(true);
  }

  closeApplyModal(): void {
    this.showApplyModal.set(false);
  }

  submitLeaveRequest(): void {
    if (!this.fromDate() || !this.toDate()) {
      this.notification.show('Please select from and to dates', 'error');
      return;
    }

    if (!this.reason().trim()) {
      this.notification.show('Please provide a reason for the leave request', 'error');
      return;
    }

    this.isSubmitting.set(true);

    const newRequest: MyLeaveRequest = {
      id: `LR-${Math.floor(1000 + Math.random() * 9000)}`,
      leaveType: this.leaveType(),
      fromDate: this.fromDate(),
      toDate: this.toDate(),
      days: this.daysCount() || 1,
      reason: this.reason().trim(),
      status: 'Pending',
      appliedOn: 'Today',
      approver: 'HR Manager',
    };

    setTimeout(() => {
      this.myRequests.update((list) => [newRequest, ...list]);
      this.isSubmitting.set(false);
      this.closeApplyModal();
      this.notification.show('Leave request submitted successfully!', 'success');
      this.reason.set('');
    }, 400);
  }
}
