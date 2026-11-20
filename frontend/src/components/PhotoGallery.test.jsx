import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import PhotoGallery from './PhotoGallery'

const photos = [
  { url: '/images/shops/a.jpg', alt_text: 'Kafe salonu' },
  { url: '/images/shops/b.jpg', alt_text: 'Latte art' },
]

describe('PhotoGallery (case 3.3)', () => {
  it('ilk fotoğrafı kapak olarak gösterir', () => {
    render(<PhotoGallery photos={photos} shopName="Test" />)

    expect(screen.getByRole('img', { name: 'Kafe salonu' })).toHaveAttribute('src', '/images/shops/a.jpg')
  })

  it('küçük resme tıklayınca büyük fotoğraf değişir', async () => {
    render(<PhotoGallery photos={photos} shopName="Test" />)

    await userEvent.click(screen.getByRole('button', { name: /Fotoğraf 2/ }))

    expect(screen.getByRole('img', { name: 'Latte art' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Fotoğraf 2/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('fotoğraf yoksa boş durum gösterir', () => {
    render(<PhotoGallery photos={[]} shopName="Test" />)

    expect(screen.getByLabelText('Test için fotoğraf yok')).toBeInTheDocument()
  })
})
