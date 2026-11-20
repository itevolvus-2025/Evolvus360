import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, throwError } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { RoleDto, RoleListResponse, RoleUpdatePayload } from '../../../core/models/api.models';

export type RoleStatus = 'Active' | 'Inactive' | 'Deactive' | 'Pending';

export interface RoleRow {
  id: number | string;
  role: string;
  purpose: string;
  status: RoleStatus;
  scope: string;
  permissions?: string[];
  reasonForChange?: string;
  effectiveDate?: string;
  role_code?: string;
}

@Injectable({ providedIn: 'root' })
export class RoleService {
  private readonly apiService = inject(ApiService);

  /** Live dataset of roles backed by API and optimistic state */
  readonly roles = signal<RoleRow[]>([
    {
      id: 1,
      role: 'Super Admin',
      purpose: 'Full control of access',
      status: 'Active',
      scope: 'Department',
      permissions: [
        'Dashboard',
        'Role Management',
        'User Management',
        'Approval',
        'Project',
        'Leave Request',
        'Leave Management',
      ],
      effectiveDate: '17-11-2026',
    },
    {
      id: 2,
      role: 'HR Manager',
      purpose: 'Manage employee records',
      status: 'Active',
      scope: 'Department',
      permissions: [
        'Dashboard',
        'User Management',
        'Approval',
        'Leave Request',
        'Leave Management',
      ],
      effectiveDate: '17-11-2026',
    },
    {
      id: 3,
      role: 'Employee',
      purpose: 'Standard self-service',
      status: 'Active',
      scope: 'Department',
      permissions: ['Dashboard', 'Project', 'Leave Request'],
      effectiveDate: '17-11-2026',
    },
    {
      id: 4,
      role: 'Consultant',
      purpose: 'Standard self-service',
      status: 'Active',
      scope: 'Department',
      permissions: ['Dashboard', 'Project', 'Leave Request'],
      effectiveDate: '17-11-2026',
    },
  ]);

  /** Loading state indicator */
  readonly isLoading = signal(false);

  constructor() {
    this.loadRoles();
  }

  /**
   * Fetch roles from backend API (GET /api/v1/roles).
   * Falls back to default roles if offline or not yet seeded.
   */
  loadRoles(): void {
    this.isLoading.set(true);
    this.apiService.get<RoleListResponse>(API_ENDPOINTS.roles.list).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        const items = res?.data?.items;
        if (Array.isArray(items) && items.length > 0) {
          const mapped: RoleRow[] = items.map((r: RoleDto) => ({
            id: r.id,
            role: r.role || r.name || r.role_name || 'Role',
            purpose: r.purpose || r.description || 'Access role',
            status: (r.status === 'Active' || r.status === 'ACTIVE' || r.is_active
              ? 'Active'
              : 'Deactive') as RoleStatus,
            scope: 'Department',
            permissions: r.permissions || [],
            effectiveDate: '17-11-2026',
            role_code: r.role_code,
          }));
          this.roles.set(mapped);
          console.log(`[RoleService] Loaded ${mapped.length} roles from backend API.`);
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        console.warn(
          '[RoleService] Backend offline or unavailable, keeping local roles:',
          err.message
        );
      },
    });
  }

  getRoleById(id: number | string): RoleRow | undefined {
    return this.roles().find((r) => String(r.id) === String(id));
  }

  /**
   * Fetch single role detail from backend API (GET /api/v1/roles/{id})
   */
  getRoleFromApi(id: number | string): Observable<RoleRow | null> {
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id));
    if (!isUuid || String(id).startsWith('temp_')) {
      const local = this.getRoleById(id);
      return of(local || null);
    }

    return this.apiService.get<RoleDto>(API_ENDPOINTS.roles.detail(id)).pipe(
      map((res) => {
        if (res && res.data) {
          const r = res.data;
          const mapped: RoleRow = {
            id: r.id,
            role: r.role || r.name || r.role_name || 'Role',
            purpose: r.purpose || r.description || '',
            status: (r.status === 'Active' || r.status === 'ACTIVE' || r.is_active
              ? 'Active'
              : 'Deactive') as RoleStatus,
            scope: 'Department',
            permissions: r.permissions || [],
            effectiveDate: '17-11-2026',
            role_code: r.role_code,
          };
          this.roles.update((list) => {
            const idx = list.findIndex((x) => String(x.id) === String(id));
            if (idx >= 0) {
              const updatedList = [...list];
              updatedList[idx] = { ...updatedList[idx], ...mapped };
              return updatedList;
            }
            return [mapped, ...list];
          });
          return mapped;
        }
        return this.getRoleById(id) || null;
      }),
      catchError((err) => {
        console.warn(`[RoleService] Could not fetch role ${id} from API, using local fallback:`, err.message);
        return of(this.getRoleById(id) || null);
      })
    );
  }

  /**
   * Create role with backend API sync (POST /api/v1/roles)
   * and optimistic local state.
   */
  addRole(roleData: Omit<RoleRow, 'id'>): Observable<RoleRow> {
    const tempId = `temp_${Date.now()}`;
    const newRole: RoleRow = {
      id: tempId,
      ...roleData,
    };

    // Optimistically update list
    this.roles.update((list) => [newRole, ...list]);

    // Send to Backend API
    return this.apiService
      .post<RoleDto>(API_ENDPOINTS.roles.create, {
        name: roleData.role.trim(),
        description: roleData.purpose?.trim(),
        permissions: roleData.permissions || [],
        status: roleData.status.toLowerCase() === 'active' ? 'active' : 'inactive',
      })
      .pipe(
        map((res) => {
          if (res?.data?.id) {
            const persisted: RoleRow = {
              ...newRole,
              id: res.data.id,
              role_code: res.data.role_code,
            };
            this.roles.update((list) =>
              list.map((r) => (r.id === tempId ? persisted : r))
            );
            console.log(`[RoleService] Role persisted to backend with ID ${res.data.id}`);
            return persisted;
          }
          return newRole;
        }),
        catchError((err: Error) => {
          console.warn('[RoleService] Backend create call failed, preserved locally:', err.message);
          return of(newRole);
        })
      );
  }

  /**
   * Update role with backend API sync (PUT /api/v1/roles/{id})
   */
  updateRole(id: number | string, updated: Partial<RoleRow>): Observable<RoleRow> {
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id));

    // Update in-memory signals immediately for responsive UI
    this.roles.update((list) =>
      list.map((r) => (String(r.id) === String(id) ? { ...r, ...updated } : r))
    );

    const existing = this.getRoleById(id);
    const fallbackRole: RoleRow = {
      ...(existing || {
        id,
        role: updated.role || 'Role',
        purpose: updated.purpose || '',
        status: updated.status || 'Active',
        scope: 'Department',
        permissions: updated.permissions || [],
        effectiveDate: '17-11-2026',
      }),
      ...updated,
    };

    // If ID is not a backend UUID (e.g. offline mock or local), return local role
    if (!isUuid || String(id).startsWith('temp_')) {
      return of(fallbackRole);
    }

    const payload: RoleUpdatePayload = {
      name: updated.role?.trim(),
      description: updated.purpose?.trim(),
      permissions: Array.isArray(updated.permissions) ? updated.permissions : [],
      status: updated.status
        ? updated.status.toLowerCase() === 'active'
          ? 'active'
          : 'inactive'
        : undefined,
    };

    return this.apiService.put<RoleDto>(API_ENDPOINTS.roles.update(id), payload).pipe(
      map((res) => {
        if (res && res.data) {
          const r = res.data;
          const mapped: RoleRow = {
            id: r.id,
            role: r.role || r.name || r.role_name || updated.role || 'Role',
            purpose: r.purpose || r.description || updated.purpose || '',
            status: (r.status === 'Active' || r.status === 'ACTIVE' || r.is_active
              ? 'Active'
              : 'Deactive') as RoleStatus,
            scope: 'Department',
            permissions: r.permissions || updated.permissions || [],
            effectiveDate: '17-11-2026',
            role_code: r.role_code || existing?.role_code,
          };
          this.roles.update((list) =>
            list.map((item) => (String(item.id) === String(id) ? mapped : item))
          );
          console.log(`[RoleService] Role ${id} updated on backend successfully.`);
          return mapped;
        }
        return fallbackRole;
      }),
      catchError((err: Error) => {
        console.error(`[RoleService] Backend update failed for ${id}:`, err.message);
        return throwError(() => err);
      })
    );
  }

  /**
   * Delete / deactivate role with backend API sync (DELETE /api/v1/roles/{id})
   */
  deleteRole(id: number | string): Observable<boolean> {
    this.roles.update((list) => list.filter((r) => String(r.id) !== String(id)));

    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id));
    if (isUuid) {
      return this.apiService.delete<void>(API_ENDPOINTS.roles.delete(id)).pipe(
        map(() => true),
        catchError((err) => {
          console.warn(`[RoleService] Backend delete failed for ${id}:`, err.message);
          return of(false);
        })
      );
    }
    return of(true);
  }
}
