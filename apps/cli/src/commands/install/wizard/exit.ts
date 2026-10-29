export class WizardExit extends Error {
  constructor(
    readonly code: number,
    message: string,
  ) {
    super(message)
    this.name = 'WizardExit'
  }
}
