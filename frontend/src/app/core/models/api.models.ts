/**
 * Standard backend response envelope matching FastAPI ApiResponse[T]
 */
export interface ApiResponse<T> {
  statusCode: number;
  message: string;
  data: T;
}

export interface ApiErrorResponse {
  statusCode?: number;
  message?: string;
  detail?: string | Array<{ loc: string[]; msg: string; type: string }>;
}

export interface AuthRoleDto {
  id: string;
  name: string;
  code: string;
}

export interface AuthUserDto {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  roles: AuthRoleDto[];
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: AuthUserDto;
  permissions: string[];
}

export interface RoleDto {
  id: string;
  name: string;
  role: string;
  role_name?: string;
  role_code?: string;
  description?: string;
  purpose?: string;
  status: string;
  is_active?: boolean;
  permissions: string[];
  created_at?: string;
  updated_at?: string;
}

export interface RoleListResponse {
  items: RoleDto[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface RoleCreatePayload {
  name: string;
  description?: string;
  purpose?: string;
  permissions?: string[];
  status?: string;
  role_code?: string;
}

export interface RoleUpdatePayload {
  name?: string;
  description?: string;
  purpose?: string;
  permissions?: string[];
  status?: string;
}
