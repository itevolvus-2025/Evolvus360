import { Component, inject, signal } from '@angular/core';
import { NotificationService } from '../../../../core/services/notification.service';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';

export interface EntityStat {
  code: string;
  color: string;
  percentage: number;
  users: number;
}

export interface PendingAction {
  id: number;
  initials: string;
  name: string;
  time: string;
  type: string;
  quote: string;
}

export interface BirthdayItem {
  name: string;
  role: string;
  initials: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [IconComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent {
  private readonly notification = inject(NotificationService);

  // Top KPI Metric counters matching the enterprise workforce design
  readonly totalUsers = signal(3);
  readonly activeUsers = signal(0);
  readonly requestsPending = signal(0);
  readonly profilesSubmitted = signal(0);

  // Entities Distribution
  readonly entities = signal<EntityStat[]>([
    { code: 'ETPL', color: '#2563eb', percentage: 33, users: 35 },
    { code: 'ES', color: '#059669', percentage: 33, users: 35 },
    { code: 'EBPL', color: '#b45309', percentage: 34, users: 38 },
    { code: 'RLPL', color: '#4d7c0f', percentage: 34, users: 38 },
    { code: 'NLLP', color: '#be123c', percentage: 34, users: 38 }
  ]);

  // Pending Actions
  readonly pendingActions = signal<PendingAction[]>([
    {
      id: 1,
      initials: 'JD',
      name: 'Jhon Doe',
      time: '09:45 AM',
      type: 'Late punch regularization: ',
      quote: '"Biometric sensor timeout at Gate 3"'
    }
  ]);

  // Birthdays Today
  readonly birthdays = signal<BirthdayItem[]>([
    {
      name: 'Linda Martinez',
      role: 'Senior Designer',
      initials: 'LM'
    },
    {
      name: 'Linda Martinez',
      role: 'Senior Designer',
      initials: 'LM'
    }
  ]);

  approveAction(id: number, name: string): void {
    this.pendingActions.update((items) => items.filter((item) => item.id !== id));
    this.notification.success(`Approved late punch regularization request for ${name}.`);
  }

  rejectAction(id: number, name: string): void {
    this.pendingActions.update((items) => items.filter((item) => item.id !== id));
    this.notification.info(`Rejected request for ${name}.`);
  }

  wishAll(): void {
    this.notification.success('Warm birthday wishes sent to all team members! 🎂🎉');
  }

  wishMember(name: string): void {
    this.notification.success(`Birthday wish sent to ${name}! 🎂`);
  }
}
