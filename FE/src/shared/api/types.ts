export type ApiSuccess<T> = {
  success: true;
  data: T;
  message?: string | null;
  requestId?: string | null;
};

export type ApiFailure = {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Array<{ field?: string | null; reason: string }>;
  };
  requestId?: string | null;
};

export type ApiEnvelope<T> = ApiSuccess<T> | ApiFailure;

export type AuthUser = {
  id: string;
  role: string;
  email: string;
  name: string;
  profileCompleted: boolean;
  createdAt: string;
};

export type AuthSession = {
  user: AuthUser;
  expiresIn: number;
};

export type Pagination = {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  hasNext: boolean;
  hasPrev: boolean;
};
