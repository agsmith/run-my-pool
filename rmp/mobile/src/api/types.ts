export type User = { id: string; email: string; display_name?: string | null; role: 'USER' | 'POOL_ADMIN' | 'SUPER_ADMIN'; is_active: boolean; email_verified: boolean };
export type Pool = { id: string; name: string; pool_type: 'survivor' | 'pickem' | 'squares'; is_public?: boolean; role?: string; member_count?: number };
export type MobileSession = { access_token: string; refresh_token: string; refresh_expires_in: number; token_type: 'bearer' };
