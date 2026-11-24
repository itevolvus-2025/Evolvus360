import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { RoleService, RoleStatus } from '../../data-access/role.service';
import { AVAILABLE_PERMISSIONS } from '../../../../core/constants/permissions.constant';

import { DropdownComponent, DropdownOption } from '../../../../shared/ui/dropdown';

@Component({
  selector: 'app-role-edit',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent, DropdownComponent],
  templateUrl: './role-edit.component.html',
  styleUrl: './role-edit.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleEditComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly roleService = inject(RoleService);
  private readonly notification = inject(NotificationService);

  readonly roleId = signal<number | string>('');

  // Form Fields
  readonly roleName = signal('');
  readonly purpose = signal('');
  readonly status = signal<RoleStatus>('Active');
  readonly reasonForChange = signal('');
  readonly effectiveDate = signal('');

  readonly statusOptions: DropdownOption[] = [
    { label: 'Active', value: 'Active' },
    { label: 'Deactive', value: 'Deactive' },
    { label: 'Inactive', value: 'Inactive' },
  ];

  // Permissions array centralized and passed to/from API
  readonly availablePermissions = AVAILABLE_PERMISSIONS;

  readonly selectedPermissions = signal<string[]>([]);

  // Delete modal state
  readonly showDeleteModal = signal(false);

  // Submitting / Saving state
  readonly isSaving = signal(false);

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      const id: number | string = /^\d+$/.test(idParam) ? parseInt(idParam, 10) : idParam;
      this.roleId.set(id);

      const existing = this.roleService.getRoleById(id);
      if (existing) {
        this.populateForm(existing);
      }

      // If id is a backend UUID string, fetch latest authoritative record from GET /api/v1/roles/{id}
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id));
      if (isUuid) {
        this.roleService.getRoleFromApi(id).subscribe({
          next: (role) => {
            if (role) {
              this.populateForm(role);
            }
          },
          error: (err: Error) => {
            console.warn(`[RoleEdit] Could not fetch role ${id} from API:`, err.message);
          },
        });
      }
    }
  }

  private populateForm(role: {
    role: string;
    purpose: string;
    status: RoleStatus;
    reasonForChange?: string;
    effectiveDate?: string;
    permissions?: string[];
  }): void {
    this.roleName.set(role.role || '');
    this.purpose.set(role.purpose || '');
    this.status.set(role.status || 'Active');
    if (role.reasonForChange) {
      this.reasonForChange.set(role.reasonForChange);
    }
    if (role.effectiveDate) {
      this.effectiveDate.set(role.effectiveDate);
    }
    if (role.permissions && Array.isArray(role.permissions)) {
      this.selectedPermissions.set([...role.permissions]);
    }
  }

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

    this.isSaving.set(true);

    this.roleService
      .updateRole(this.roleId(), {
        role: name,
        purpose: this.purpose().trim(),
        status: this.status(),
        reasonForChange: this.reasonForChange().trim() || 'Role details updated via administration console',
        permissions: this.selectedPermissions(),
        effectiveDate: this.effectiveDate().trim() || new Date().toISOString().slice(0, 10),
      })
      .subscribe({
        next: () => {
          this.isSaving.set(false);
          this.notification.show(`Role "${name}" updated successfully!`, 'success');
          void this.router.navigateByUrl('/administration');
        },
        error: (err: Error) => {
          this.isSaving.set(false);
          this.notification.show(
            err.message || 'Failed to update role. Please verify your inputs.',
            'error'
          );
        },
      });
  }

  openDeleteConfirm(): void {
    this.showDeleteModal.set(true);
  }

  closeDeleteConfirm(): void {
    this.showDeleteModal.set(false);
  }

  confirmDelete(): void {
    const name = this.roleName();
    this.roleService.deleteRole(this.roleId()).subscribe({
      next: () => {
        this.showDeleteModal.set(false);
        this.notification.show(`Role "${name}" has been deleted.`, 'info');
        void this.router.navigateByUrl('/administration');
      },
      error: (err: Error) => {
        this.showDeleteModal.set(false);
        this.notification.show(err.message || 'Failed to delete role.', 'error');
      },
    });
  }
}
