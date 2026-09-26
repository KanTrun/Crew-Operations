/**
 * Hình dạng diff phân công — dùng chung cho panel nhật ký và cho /doi-ca.
 *
 * Vì sao tách khỏi component: `/doi-ca` cần cùng hình dạng này nhưng KHÔNG nên
 * import từ một tệp component (kéo theo `apiGet`, `kit`, React state vào một
 * trang chỉ muốn khai kiểu). Khai kiểu ở tệp riêng thì cả hai nơi dùng đúng một
 * định nghĩa, và không có phụ thuộc chéo giữa hai trang.
 *
 * Phải khớp `ca_api/services/schedule_diff.so_sanh_phan_cong`.
 */

export type CaInfo = {
  ca_id: string;
  thu: string;
  khung: string;
  gio: string;
  vi_tri?: string;
};

export type NguoiDon = { nv_id: string; ten: string };

export type DongThayDoi = {
  ca: CaInfo;
  nv_id: string;
  ten: string;
  /** "vao" hoặc "ra" */
  chieu: string;
};

export type HoanDoi = {
  ca: CaInfo;
  ra: NguoiDon[];
  vao: NguoiDon[];
};

export type ChuyenCa = {
  nv_id: string;
  ten: string;
  tu_ca: CaInfo[];
  den_ca: CaInfo[];
};

export type Diff = {
  them: DongThayDoi[];
  bot: DongThayDoi[];
  hoan_doi: HoanDoi[];
  doi_giua_hai_ca: ChuyenCa[];
  giu_nguyen: number;
  khong_so_sanh_duoc: boolean;
};
