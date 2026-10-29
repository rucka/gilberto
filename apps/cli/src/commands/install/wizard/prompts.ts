import { checkbox, confirm, input } from '@inquirer/prompts'

export type WizardPrompts = {
  input: (o: { message: string; default?: string }) => Promise<string>
  confirm: (o: { message: string; default?: boolean }) => Promise<boolean>
  checkbox: (o: {
    message: string
    choices: readonly { value: string; checked: boolean }[]
  }) => Promise<string[]>
}

export const inquirerPrompts: WizardPrompts = {
  input: o => input(o),
  confirm: o => confirm(o),
  checkbox: o => checkbox({ message: o.message, choices: o.choices.map(c => ({ ...c })) }),
}
