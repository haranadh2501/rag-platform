import { apiRequest } from './apiClient';
import type { UserList, UserOut, InviteUserRequest } from '@admin-types';

export async function listUsersApi(): Promise<UserList> {
  return apiRequest<UserList>('GET', '/admin/users');
}

export async function createUserApi(input: InviteUserRequest): Promise<UserOut> {
  return apiRequest<UserOut>('POST', '/auth/register', input);
}
