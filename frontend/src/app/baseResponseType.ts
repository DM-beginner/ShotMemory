/**
 * 统一响应格式
 */
export interface BaseResponse<T> {
  code: number;
  message: string;
  data: T;
}
