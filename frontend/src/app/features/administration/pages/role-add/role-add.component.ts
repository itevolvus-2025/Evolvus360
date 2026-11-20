import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { RoleService, RoleStatus } from '../../data-access/role.service';
import { AVAILABLE_PERMISSIONS } from '../../../../core/constants/permissions.constant';

@Component({
  selector: 'app-role-add',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  templateUrl: './role-add.component.html',
  styleUrl: './role-add.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleAddComponent {
  private readonly router = inject(Router);
  private readonly roleService = inject(RoleService);
  private readonly notification = inject(NotificationService);

  // Form Fields
  readonly roleName = signal('');
  readonly purpose = signal('');
  readonly status = signal<RoleStatus>('Active');
  readonly effectiveDate = signal('');

  // Permissions array centralized and passed to/from API
  readonly availablePermissions = AVAILABLE_PERMISSIONS;

  readonly selectedPermissions = signal<string[]>([]);

  readonly isSaving = signal(false);

  isPermissionChecked(perm: string): boolean {
    return this.selectedPermissions().includes(perm);
  }

  togglePermission(perm: string): void {
    this.selectedPermissions.update((list) => {
      if (list.includes(perm)) {
        return list.filter((p) => p !== perm);
      }
      return [...list, perm];
    });
  }

  saveRole(): void {
    if (this.isSaving()) return;

    const name = this.roleName().trim();
    if (!name) {
      this.notification.show('Role name is mandatory', 'error');
      return;
    }

    if (!this.status()) {
      this.notification.show('Please select a status', 'error');
      return;
    }

    this.isSaving.set(true);

    this.roleService
      .addRole({
        role: name,
        purpose: this.purpose().trim() || 'Standard enterprise role',
        status: this.status(),
        scope: 'Department',
        permissions: this.selectedPermissions(),
        effectiveDate: this.effectiveDate().trim() || new Date().toISOString().slice(0, 10),
      })
      .subscribe({
        next: () => {
          this.isSaving.set(false);
          this.notification.show(`Role "${name}" created successfully!`, 'success');
          void this.router.navigateByUrl('/administration');
        },
        error: (err: Error) => {
          this.isSaving.set(false);
          this.notification.show(err.message || 'Failed to create role', 'error');
        },
      });
  }
}
