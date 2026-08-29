/**
 * Things you may want to change without going near the app code.
 */

export const PAYMENT = {
  /**
   * Show the donation box before entering the temple.
   *
   * Be aware of what this can and cannot do: the app is a static page, so a
   * visitor can skip this screen from the browser console in seconds. Treat it
   * as an honour-system ตู้บริจาค, not as access control. Real enforcement
   * needs a server that verifies the transfer before serving the app.
   */
  enabled: true,

  /** Ask again only after this many days. 0 asks every visit. */
  rememberDays: 30,

  qr: 'assets/pay/promptpay-qr.jpg',
  /** Shown under the QR. Leave empty to rely on the name printed in the image. */
  payee: 'ดรากร หวานสนิท',

  /** Leave empty for ตามกำลังศรัทธา, or set e.g. '๒๐ บาท'. */
  amount: '',

  /** Set false to let visitors in without confirming. */
  required: true,
};
